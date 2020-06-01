"""
Export CDCRApp annotations to CONLL format
"""

import spacy
import json
import os
import random

from tqdm.auto import tqdm
from typing import List, Optional, Iterator
from .model import Task, UserTask, NewsArticle, SciPaper
from collections import defaultdict, OrderedDict
from urllib.parse import urlparse
from transformers import BertModel, BertTokenizerFast



def map_pairs(task_group: List[Task]):
    """Map coreference pairs from annotations to the documents"""
    news_bounds = []
    sci_bounds = []

    cluster2idx = {}

    for task in task_group:
        _,start,end = task.news_ent.split(";")

        start = int(start)
        end = int(end)

        cluster_id = task.id


        news_bounds.append((start,end, cluster_id))

        cluster2idx[cluster_id] = len(news_bounds)-1

        _,start,end = task.sci_ent.split(";")
        start = int(start)
        end = int(end)

        sci_bounds.append((start,end, cluster_id))

    smol2lrg = sorted(news_bounds, key=lambda x: x[2] - x[1])


    merge = {}
    # tidy overlapping boundaries 
    for start, end, clusterid in sorted(news_bounds, key=lambda x: x[2] - x[1], reverse=True):
        

        if clusterid in merge:
            continue

        for nstart, nend, nclusterid in smol2lrg:

            if (start,end,clusterid) == (nstart,nend, nclusterid):
                continue
            
            if (start <= nstart) and (end >= nend):
                merge[nclusterid] = clusterid
                print(f"Merge news {nclusterid} -> {clusterid}")

    news_bounds = [x for x in news_bounds if x[2] not in merge]

    sci_bounds = [(start,end, merge[old_id]) if old_id in merge else (start,end,old_id) for start,end,old_id in sci_bounds]

    sci_smol2lrg = sorted(sci_bounds, key=lambda x: x[2] - x[1])
    
    merge = {}
    merged = {value:key for key,value in merge.items()}
    prune = set()
    for idx, (start,end,clusterid) in enumerate(sorted(sci_bounds, key=lambda x: x[2] - x[1], reverse=True)):

        #if clusterid in merge:
        #    continue

        if idx in prune:
            continue

        for nidx, (nstart, nend, nclusterid) in enumerate(sci_smol2lrg):

            if (start,end,clusterid) == (nstart,nend, nclusterid):
                continue
            
            if (start <= nstart) and (end >= nend):
                #merge[nclusterid] = clusterid

                if nclusterid in merged:
                     print(f"Map {clusterid} onto {merged[nclusterid]}")
                     merge[clusterid] = merged[nclusterid]

                prune.add(nidx)
                print(f"Prune {nidx} (clusterid={nclusterid}) inside (clusterid={clusterid})")
                #print(f"Merge science {nclusterid} -> {clusterid}")

    new_sci_bounds = []

    for idx, (start,end,clusterid) in enumerate(sci_smol2lrg):

        if idx in prune:
            continue

        if clusterid in merge:
            new_sci_bounds.append((start,end,merge[clusterid]))
        else:
            new_sci_bounds.append((start,end,clusterid))

            
    

    return news_bounds, new_sci_bounds


def check_bounds(bounds, word_idx, word_len, retstr=True):
    """Check if a word is of interest"""

    for start,end,cluster_id in bounds:
        if word_idx > end:
            continue

        if word_idx >= start and word_idx < end:

            if (word_idx == start) and (word_idx + word_len) == end:
                return f"({cluster_id})" if retstr else (cluster_id, True, True)


            if word_idx == start:
                return f"({cluster_id}" if retstr else (cluster_id, True, False)

            elif (word_idx + word_len) == end:
                return f"{cluster_id})" if retstr else (cluster_id, False, True)

            else:
                return "-" if retstr else (cluster_id, False, False)
        
    return None

def check_sent_bounds(bounds, sent_start, sent_end):
    """Inverse of check_bounds - see if a sentence contains a word"""

    for start,end,cluster_id in bounds:

        if sent_start > end:
            continue

        if start >= sent_start and end <= sent_end:
            
            return str(cluster_id)
        
    return None


def map_and_sort(tasks: List[Task]) -> List[tuple]:
    """Map a list of tasks onto unique news/sci article pairs and sort"""

    task_map = defaultdict(lambda:[])

    for task in tasks:
        task_map[(task.news_article_id, task.sci_paper_id)].append(task)

    task_map_items = sorted(task_map.items(), key=lambda item: item[0][0] )
    task_map_items = sorted(task_map_items, key=lambda item: item[0][1])

    return task_map_items


def export_to_conll(input_file:str, output_file: str):
    """Given a JSON formatted set of mentions, turn into CONLL notation"""

    # open the 'complete' json file
    with open(input_file) as f:
        docs = json.load(f, object_pairs_hook=OrderedDict)

    # open the mentions file    
    entities_file = os.path.join(os.path.dirname(input_file), 
                                    os.path.splitext(os.path.basename(input_file))[0] + "_entities.json")

    with open(entities_file) as f:
        entities = json.load(f)

    ent_map = {}

    for ent in entities:

        tok_total = len(ent['tokens_ids'])
        for i, tok_id in enumerate(ent['tokens_ids']):
            
            if i == 0 and tok_total == 1:
                ent_map_val = f"({ent['cluster_id']})"
            elif i == 0:
                ent_map_val = f"({ent['cluster_id']}"

            elif (i+1) == tok_total:
                ent_map_val = f"{ent['cluster_id']})"
            else:
                ent_map_val = "-"

            ent_map[(ent['doc_id'], ent['sentence_id'], tok_id)] = ent_map_val
    
    with open(output_file, "w") as fp:
        fp.write("#begin document test_entities\n")

        for doc_id, doc in tqdm(docs.items()):

            #docs are exported with id like topic_doctype_docid e.g. 66_science_113
            topic_id = doc_id.split("_")[0]
            subtopic_id = f"{topic_id}_0"

            for sent_id, word_id, word, flag in doc:

                coref_val = ent_map.get((doc_id, sent_id, word_id), "-")

                

                row = [topic_id, subtopic_id, doc_id, str(sent_id), str(word_id), word, str(flag), coref_val]

                fp.write("\t".join(row) + "\n")

        fp.write("#end document\n")
        
def generate_json_maps(task_items: List[tuple], nlp: spacy.language.Language) -> (dict, List[dict]):
    """Generate map of document words and entities"""

    doc_map = {}
    doctypes =['news','science']
    entities = []

    for topic_idx, (_, tasklist) in enumerate(tqdm(task_items)):
    #for topic_idx, (topic_id, tasklist) in enumerate(tqdm(task_map.items())):

        scidoc = nlp(tasklist[0].sci_text)
        newsdoc = nlp(tasklist[0].news_text)

        doc_ids = [tasklist[0].newsarticle.id, tasklist[0].scipaper.id]

        docs = [newsdoc, scidoc]

        

        bounds = map_pairs(tasklist)

        for doc_idx, doc in enumerate(docs):

            doc_id = f'{topic_idx}_{doctypes[doc_idx]}_{doc_ids[doc_idx]}'

            word_rows = []
            currentCluster: Optional[dict] = None
            tok_id = 0
            for sent_idx, sent in enumerate(doc.sents):

                flag = check_sent_bounds(bounds[doc_idx], sent.start_char, sent.end_char) is not None


                for word in sent:

                    if word.is_space:
                        continue

                    res = check_bounds(bounds[doc_idx], word.idx, len(word.text), retstr=False)

                    if res is not None:
                        cluster_id, _, _ = res

                        if currentCluster is None:
                            currentCluster = {
                                "doc_id": doc_id,
                                "sentence_id": sent_idx,
                                "tokens_ids":[tok_id],
                                "topic": topic_idx,
                                "subtopic": f"{topic_idx}_{doc_idx}",
                                "tags": [word.pos_],
                                "tokens": [word.text],
                                "lemmas": [word.lemma_],
                                "cluster_id": cluster_id,
                                "cluster_desc": "something",
                                "singleton":False
                            } 
                        else:
                            currentCluster['tokens_ids'].append(tok_id)
                            currentCluster['tokens'].append(word.text)
                            currentCluster['lemmas'].append(word.lemma_)
                            currentCluster['tags'].append(word.pos_)


                    elif currentCluster is not None:

                        for key in ['tags','tokens','lemmas']:
                            currentCluster[key] = " ".join(currentCluster[key]) # pylint: disable=unsubscriptable-object,unsupported-assignment-operation

                        entities.append({x:y for x,y in currentCluster.items()})
                        currentCluster = None



                    word_rows.append([
                        sent_idx,
                        tok_id,
                        str(word.text),
                        flag
                    ])

                    tok_id += 1

            doc_map[doc_id] = word_rows
        # end doc loop
    # end topic loop
    return doc_map, entities

def test_train_split(task_map_items: List[tuple], split:float, seed:int):
    """Split a list of tasks pseudo-randomly"""


    task_count = sum([len(x) for _,x in task_map_items])

    print(f"Found {len(task_map_items)} containing {task_count} tasks")

    # work out the split
    train_amt = int(task_count * split)

    print(f"Split into {train_amt} and {task_count-train_amt} or near as possible")

    random.seed(seed)
    random.shuffle(task_map_items)

    # generate splits
    train_set = []
    train_task_count = 0
    test_set = []

    for topic_id, tasklist in task_map_items:
        
        if train_task_count < train_amt:
            train_set.append((topic_id, tasklist))
            train_task_count += len(tasklist)
        else:
            test_set.append((topic_id, tasklist))

    return train_set, test_set

def export_to_json(tasks: List[Task], output_file: str, split:float,seed:int):
    """Export to JSON format compatible with Arie's coref model"""

    # first we generate arrays of words within files
    nlp = spacy.load('en', disable=['textcat'])

    task_map = defaultdict(lambda:[])

    for task in tasks:
        task_map[(task.news_article_id, task.sci_paper_id)].append(task)

    doc_map = {}

    task_map_items = map_and_sort(tasks)

    train_set, test_set = test_train_split(task_map_items, split, seed)

    outdir = os.path.dirname(output_file)
    basename = os.path.basename(output_file)
    namestub, ext = os.path.splitext(basename)

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    for split_name, items in zip(['train', 'test'], [train_set, test_set]):
        outfile = os.path.join(outdir, f"{namestub}_{split_name}{ext}")
        entfile = os.path.join(outdir, f"{namestub}_{split_name}_entities{ext}")

        doc_map, entities = generate_json_maps(items, nlp)

        with open(outfile,"w") as f:
            json.dump(doc_map, f, indent=2)

        with open(entfile, "w") as f:
            json.dump(entities, f, indent=2)

def generate_joshi_jsondocs(task_map_items, tokenizer: BertTokenizerFast, nlp: spacy.language.Language) -> Iterator[dict]:
    """Given a set of task items generate json docs to be serialised"""

    for task_id, task_records in tqdm(task_map_items):

        news_doc = nlp(task_records[0].news_text)
        sci_doc = nlp(task_records[0].sci_text)

        jsondoc = {
            'doc_key': f"nw",
            "clusters":[], 
            'subtoken_map':[], 
            'sentence_map':[], 
            'sentences':[], 
            'speakers':[],
            "doc_ids":[f"news_{task_id[0]}", f"science_{task_id[0]}"],
            'doc_boundaries':[]}

        sent_id = 0
        i = 0
        for doc in [news_doc, sci_doc]:
            
            jsondoc['doc_boundaries'].append(i)
            i = 0
            for sent in doc.sents:
                r = tokenizer.tokenize(sent.text, add_special_tokens=True)
                
                jsondoc['sentences'].append(r)

                jsondoc['speakers'].append(['[SPL]'] + (['-'] * (len(r) - 2)) + ['[SPL]'])

                for tok in r[:-1]:
                    jsondoc['sentence_map'].append(sent_id)
                    jsondoc['subtoken_map'].append(i)

                    if tok not in ['[CLS]'] and not tok.startswith('##'):
                        i+=1
                
                # increment sentence id 
                sent_id += 1

        yield jsondoc



def export_to_joshi(tasks: List[Task], output_file: str, split:float,seed:int):
    """Export to JOSHI jsonlines format"""

    nlp = spacy.load('en', disable=['textcat'])
    tokenizer = BertTokenizerFast.from_pretrained('../joshi_coref/data/spanbert_base')


    task_map = defaultdict(lambda:[])

    for task in tasks:
        task_map[(task.news_article_id, task.sci_paper_id)].append(task)

    task_map_items = map_and_sort(tasks)

    train_set, test_set = test_train_split(task_map_items, split, seed)

    basedir = os.path.dirname(output_file)
    basename = os.path.basename(output_file)
    namestub, ext = os.path.splitext(basename)

    testname = os.path.join(basedir, f"{namestub}_test{ext}")
    trainname = os.path.join(basedir, f"{namestub}_train{ext}")

    for taskset, outname in zip([train_set, test_set], [trainname, testname]):

        with open(outname,"w") as f:

            for jsondoc in generate_joshi_jsondocs(taskset, tokenizer, nlp):                
                f.write(json.dumps(jsondoc) + "\n")

        #end for task (doc-pair)
    #end with open output_file





