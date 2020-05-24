"""
Export CDCRApp annotations to CONLL format
"""
from tqdm.auto import tqdm
import spacy
from typing import List
from .model import Task, UserTask, NewsArticle, SciPaper
from collections import defaultdict
from urllib.parse import urlparse


def map_pairs(task_group: List[Task]):
    """Map coreference pairs from annotations to the documents"""
    news_bounds = []
    sci_bounds = []

    for task in task_group:
        _,start,end = task.news_ent.split(";")
        news_bounds.append((int(start),int(end), task.id))
        _,start,end = task.sci_ent.split(";")
        sci_bounds.append((int(start),int(end), task.id))

    return news_bounds, sci_bounds


def check_bounds(bounds, word_idx, word_len):
    """Check if a word is of interest"""

    for start,end,cluster_id in bounds:
        if word_idx > end:
            continue

        if word_idx >= start and word_idx < end:

            if word_idx == start:
                return f"({cluster_id}"

            if (word_idx + word_len) == end:
                return f"{cluster_id})"

            else:
                return "-"
        
    return None

def check_sent_bounds(bounds, sent_start, sent_end):
    """Inverse of check_bounds - see if a sentence contains a word"""

    for start,end,cluster_id in bounds:

        if sent_start > end:
            continue

        if start >= sent_start and end <= sent_end:
            
            return str(cluster_id)
        
    return None

def export_to_conll(tasks: List[Task], filename: str):
    """Export a list of tasks to conll format"""

    with open(filename, "w") as fp:

        nlp = spacy.load('en', disable=['ner','parse','textcat'])

        task_map = defaultdict(lambda:[])

        for task in tasks:
            task_map[(task.news_article_id, task.sci_paper_id)].append(task)

        for topic_idx, (topic_id, tasklist) in enumerate(tqdm(task_map.items())):

            scidoc = nlp(tasklist[0].sci_text)
            newsdoc = nlp(tasklist[0].news_text)

            docs = [newsdoc, scidoc]

            bounds = map_pairs(tasklist)


            for doc_idx, doc in enumerate(docs):
                
                for sent_idx, sent in enumerate(doc.sents):

                    flag = check_sent_bounds(bounds[doc_idx], sent.start_char, sent.end_char) is not None

                    for word_idx, word in enumerate(sent):
                        cluster_id = check_bounds(bounds[doc_idx], word.idx, len(word.text))

                        row = [str(topic_idx), 
                            f"{topic_idx}_{doc_idx}",  
                            f"{topic_id[0]}_{topic_id[1]}", 
                            str(sent_idx), 
                            str(word_idx), 
                            word.text,
                            str(flag),
                            cluster_id if cluster_id is not None else "-"]
                            

                        fp.write("\t".join(row) + "\n")

        # 

    print(len(task_map))
    