import requests
import click
import json
import datetime
import spacy
import re
import torch
import hashlib
import itertools
from lxml import etree
import numpy as np

from scipy.spatial.distance import cosine
from cdcrapp import CLIContext
from cdcrapp.model import Task
from transformers import BertModel, BertTokenizerFast

from spacy.tokens.span import Span

torch.cuda.init()

tokenizer = BertTokenizerFast.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased').cuda()
nlp = spacy.load('en')

def extract_mentions(text: str):
    """Extract named entities and noun phrases"""

    doc = nlp(text)

    return list(doc.ents) + list(doc.noun_chunks)


def get_tokens_by_offset(start:int,end:int, model_inputs: dict, second_doc=False):
    
    tokens = tokenizer.convert_ids_to_tokens(model_inputs['input_ids'])

    found_sep = False
    for i, (tok, bounds) in enumerate(zip(tokens, model_inputs['offset_mapping'])):

        if tok == '[SEP]':
            found_sep = True

        if second_doc and not found_sep:
            continue
        
        if bounds is None:
            continue
            
        s,e = bounds


        if s > end:
            break
    
        if s >= start and e <= end:
            yield i,tok

def process_pair(news_summary: str, abstract: str):
    """Given a news summary and a sci abstract, find all candidates"""

    model_inputs = tokenizer.encode_plus(text=news_summary, text_pair=abstract, 
    add_special_tokens=True, 
    return_offsets_mapping=True,
    max_length=1024,
    truncation_strategy='only_second')

    # run single pass of BERT with both documents to get attention matrices
    with torch.no_grad():
            hidden_state, out = model(
                input_ids=torch.tensor([model_inputs['input_ids']]).cuda(), 
                token_type_ids = torch.tensor([model_inputs['token_type_ids']]).cuda(),
                attention_mask = torch.tensor([model_inputs['attention_mask']]).cuda()
            )

    state = hidden_state.squeeze()
    
    # now find candidate phrases
    news_candidates = extract_mentions(news_summary)
    sci_candidates = extract_mentions(abstract)

    ncandidates = []
    for news_cand in news_candidates:

        n_tokens = list(get_tokens_by_offset(news_cand.start_char,news_cand.end_char, model_inputs))

        if len(n_tokens) < 1:
           print(f"[NEWS] No tokens found for {news_cand.text}")
           continue

        n_v = np.mean(np.array([state[i].cpu().numpy() for (i,_) in n_tokens]), axis=0)

        ncandidates.append((news_cand, n_v))

    scandidates = []
    for sci_cand in sci_candidates:
        
        s_tokens = list(get_tokens_by_offset(sci_cand.start_char, sci_cand.end_char, model_inputs, second_doc=True))

        if len(s_tokens) < 1:
            print(f"[SCI] No tokens found for {sci_cand.text}")
            continue

        s_v = np.mean(np.array([state[i].cpu().numpy() for (i,_) in s_tokens]), axis=0)

        scandidates.append((sci_cand, s_v))



    for ncand, n_v in ncandidates:

        for scand, s_v in scandidates:


            sim = 1-cosine(s_v, n_v)

            if not np.isnan(sim):
                yield ncand, scand, 1-cosine(s_v, n_v)


def tidy_abstract(abstract: str) -> str:
    """Tidy an abstract, deal with XML"""

    if "<jats" in abstract:
        doc = etree.fromstring(f"<doc xmlns:jats=\"http://www.ncbi.nlm.nih.gov/JATS1\">{abstract}</doc>")
        ps = doc.findall(".//{http://www.ncbi.nlm.nih.gov/JATS1}p")
        text = " ".join([" ".join(p.itertext()) for p in ps])
        return text

    if "<p>" in abstract:
        doc = etree.fromstring(f"<doc>{abstract}</doc>")
        ps = doc.findall(".//p")
        text = " ".join([" ".join(p.itertext()) for p in ps])
        return text
    else:
        return abstract




@click.command()
@click.option("--endpoint", type=str, default="http://localhost:4000/api/newsarticles")
@click.option("--summarizer_endpoint", type=str, default="http://localhost:8000/")
def main(endpoint, summarizer_endpoint):
    """Ingest new tasks from harri core server"""
    
    ctx = CLIContext()
    
    r = requests.get(endpoint)
    response = r.json()
    
    pages = response['totalPages']
    page = 0

    hashes = set()
    
    for page in range(pages):
        print(f"Page {page+1} of {pages}")
        r = requests.get(endpoint, params={"page":page})
        response = r.json()
        
        for item in response['items']:
            
            print("----------------------")
            
            
 
            #item must have at least 1 paper with an abstract
            hasAbstract = False
            for paper in item['ScientificPapers']:
                if paper['abstract'].strip() != "":
                    hasAbstract = True
                    break
                
            if not hasAbstract:
                print(f"No papers with abstracts found for article {item['url']}")
                print("skipping...")
                continue

            if item['fullText'].strip() == "":
                print(f"No content found in article {item['url']} so skipping it...")
                continue
            
            tasks = ctx.tasksvc.list(Task, filters={"news_url": item['url']})

            if len(tasks) > 0:
                print(f"Article {item['title']} - {item['url']} already in database")
            else:
                print(f"Ingest {item['url']}")

                # tidy up abstract
                abstract = tidy_abstract(paper['abstract'])
                
                # generate summary
                r = requests.post(summarizer_endpoint, json={"text":item['fullText']})
                summary = r.json()['summary']
                
                print(f"Summary for {item['url']}: {summary}")

                print("--")

                print(f"Abstract {abstract}")

                print("Process document pair, generate comparisons...")

                new_tasks = []
                for news_cand, sci_cand, sim in process_pair(summary, abstract):
                    

                    if sim > 0.3:
                        
                        task = Task()
                        task.news_url = item['url']
                        task.news_text = summary
                        task.news_ent = f"{news_cand.text};{news_cand.start_char};{news_cand.end_char}"
                        task.sci_ent = f"{sci_cand.text};{sci_cand.start_char};{sci_cand.end_char}"
                        task.sci_text = abstract
                        task.sci_url = paper['doi']
                        task.similarity = sim
                        task.hash = hashlib.new("sha256", task.news_url.encode() + 
                            task.sci_url.encode() + 
                            task.news_ent.encode() + 
                            task.sci_ent.encode()).hexdigest()

                        if task.hash not in hashes:
                            hashes.add(task.hash)
                            new_tasks.append(task)

                if len(new_tasks) > 0:
                    print(f"Add {len(new_tasks)} new tasks to database")
                    ctx.tasksvc.add_tasks(new_tasks)






if __name__ == "__main__":
    main() # pylint: disable=no-value-for-parameter