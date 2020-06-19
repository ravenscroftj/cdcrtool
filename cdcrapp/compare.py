"""Compare Arie model output with annotations"""

import pickle
import logging
import spacy

from typing import List
from cdcrapp.export import map_and_sort
from cdcrapp.model import Task
from collections import defaultdict

from itertools import combinations

logging.basicConfig(level=logging.INFO)

def compare(pklfile: str, task_group: List[Task]):

    nlp = spacy.load('en')
    logger = logging.getLogger(__name__)

    logger.info("Prepare known tasks from db")
    task_items = {k:v for k,v in  map_and_sort(task_group) }

    pred_tasks = {}

    logger.info("Load predictions")
    with open(pklfile,'rb') as f:
        documents, all_clusters, doc_ids, starts, ends = pickle.load(f)

    logger.info("Group predictions by document pairs")
    doc_topics = defaultdict(lambda:{})

    for docname in documents.keys():
        topic, doctype, docid = docname.split("_")
        doc_topics[topic][doctype] = int(docid)


    docid2spacy = {}
    for topic,doc_pair in doc_topics.items():

        tasklist = task_items[(doc_pair['news'], doc_pair['science'])]

        scidoc = nlp(tasklist[0].sci_text)
        newsdoc = nlp(tasklist[0].news_text)

        docid2spacy[f"{topic}_news_{doc_pair['news']}"] = newsdoc
        docid2spacy[f"{topic}_science_{doc_pair['science']}"] = scidoc


    logger.info("Locate predictions")
    candidates = []
    for cluster in all_clusters.values():

        newsdoc = None
        scidoc = None

        for mention1, mention2 in combinations(cluster, 2):

            if ("news" in doc_ids[mention1] and "science" in doc_ids[mention2]):

                newsmention = mention1
                scimention = mention2

            elif ("science" in doc_ids[mention1] and "news" in doc_ids[mention2]):
                newsmention = mention2
                scimention = mention1
                
            else:
                continue

            news_id = int(doc_ids[newsmention].split("_")[2])
            sci_id = int(doc_ids[scimention].split("_")[2])
            newsdoc = docid2spacy[doc_ids[newsmention]]
            scidoc = docid2spacy[doc_ids[scimention]]

            news_tokens = newsdoc[starts[newsmention]:ends[newsmention]+1]
            #print("news spacy:",news_tokens)
            #print("news model:",documents[doc_ids[newsmention]][starts[newsmention]:ends[newsmention]+1])
            news_start = news_tokens[0].idx
            #print(news_tokens[0])
            
            news_end = news_tokens[-1].idx + len(news_tokens[-1])
            #print(news_tokens[-1])
            #print(news_start, news_end)
            news_text = f"{newsdoc.text[news_start:news_end]};{news_start};{news_end}"

            sci_tokens = scidoc[starts[scimention]:ends[scimention]+1]
            #print("sci spacy:",sci_tokens)
            #print("sci model:",documents[doc_ids[scimention]][starts[scimention]:ends[scimention]+1])
            sci_start = sci_tokens[0].idx
            sci_end = sci_tokens[-1].idx + len(sci_tokens[-1])
            sci_text = f"{scidoc.text[sci_start:sci_end]};{sci_start};{sci_end}"



            #print(f"{news_text} -> {sci_text}")
            
            resolved = False
            for task in task_items[(news_id, sci_id)]:

                if task.news_ent == news_text and task.sci_ent == sci_text:
                    resolved = True
                    break

            if not resolved:
                #print("Found a new candidate task")
                
                candidates.append((news_id, sci_id, news_text, sci_text))

            #relevent_tasks = task_items[(news_id, sci_id)]
    # end for cluster
    logger.info(f"Found {len(candidates)} candidate tasks")
    #print()
    return candidates





    
        