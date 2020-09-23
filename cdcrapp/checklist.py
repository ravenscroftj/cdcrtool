# %%
from dotenv import load_dotenv
from collections import Counter
from matplotlib import pyplot as plt

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload

import os
import json
import numpy as np
import pandas as pd
import seaborn as sns
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import User, Task, UserTask, NewsArticle, SciPaper


load_dotenv()

sns.set_style()

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 200)

pd.options.display.max_colwidth = 200

_engine = create_engine(os.getenv("SQLALCHEMY_DB_URI"))
_usersvc : UserService = UserService(_engine)
_tasksvc : TaskService = TaskService(_engine)
# %%
df = pd.read_csv("../checklist-tasks-v2.csv").dropna(subset=['Test Example'])
# %%
df.head()

task_types = {}
for i,row in df.iterrows():
    task_types[row['id']] = row['Test Example']

# %%
with _tasksvc.session() as session:
    q= session.query(Task)\
        .options(joinedload(Task.usertasks))\
        .filter(Task.id.in_(df['id'].tolist()))
    tasks = q.all()
    
# %%
for task in tasks:
    print(task.news_ent, task.sci_ent, task.get_best_answer())
# %%
with open("../mentions/31_07_20_5pc/test.json") as f:
    docs = json.load(f)

with open("../mentions/31_07_20_5pc/test_entities.json") as f:
    ents = json.load(f)


# %%
sci_docs = []
news_docs = []
for doc in docs.keys():
    _,ttype,id= doc.split("_")    
    
    if ttype == "news":
        news_docs.append(int(id))
    else:
        sci_docs.append(int(id))
# %%
import spacy
nlp = spacy.load('en')

news_docs = {}
sci_docs = {}

# %%

for task in tasks:
    if task.news_article_id not in news_docs:
        news_docs[task.news_article_id] = nlp(task.news_text)
    
    if task.sci_paper_id not in sci_docs:
        sci_docs[task.sci_paper_id] = nlp(task.sci_text)


#%%
def tok_id_from_doc(doc, start,end):
    tok_id = 0
    for word in doc:

        if word.is_space:
            continue

        if word.idx >= start and (word.idx+len(word)) <= end:
            yield tok_id

        tok_id += 1

#%%
from analyse import parse_conll

with open("../clustering_experiments/31_07_20_5pc_entities_scratch/test_entities_average_0.7_model_15_corpus_level.conll") as f:
    clusters, contents = parse_conll(f)
# %%

# %%
clusters
news_doc_mentions = {}
science_doc_mentions = {}
for cluster_id, cluster in clusters.items():
    for mention in cluster:
        for (doc_id, word_offset,token) in mention:
            _,doctype,did = doc_id.split("_")
            if doctype == 'news':
                news_doc_mentions[(int(did),int(word_offset))] = cluster_id
            else:
                science_doc_mentions[(int(did),int(word_offset))] = cluster_id

# %%

def check_task_result(task):

    _,start,end = task.news_ent.split(";")
    doc = nlp(task.news_text)
    news_offsets = list(tok_id_from_doc(doc,int(start),int(end)))

    _,start,end = task.sci_ent.split(";")
    doc = nlp(task.sci_text)
    sci_offsets = list(tok_id_from_doc(doc,int(start),int(end)))

    for offset in news_offsets:
        ncluster = news_doc_mentions.get((task.news_article_id, offset))

        if ncluster is not None:
            break

    for offset in sci_offsets:
        scluster = science_doc_mentions.get((task.sci_paper_id , offset))

        if scluster is not None:
            break

    if (scluster == ncluster) and (scluster != None):
        return 'yes'
    else:
        return 'no'


# %%
passes = {'yes':Counter(),'no':Counter()}
fails = {'yes':Counter(),'no':Counter()}
for task in tasks:
    actual = task.get_best_answer()
    predicted = check_task_result(task)

    if predicted != actual:
        fails[actual][task_types[task.id]] += 1
        #print(predicted, task.get_best_answer(), task_types[task.id])
    else:
        passes[actual][task_types[task.id]] += 1

# %%
for ttype in set(task_types.values()):
    print(ttype)
    for ans_type in ['yes','no']:
        total = (passes[ans_type][ttype]+fails[ans_type][ttype])
        correct = passes[ans_type][ttype]
        print("\t",ans_type, correct * 100 / total, f"({correct}/{total})")
# %%
answermap = {}
for t in tasks:
    answermap[t.id] = t.get_best_answer()

df['Answer'] = df.id.apply(lambda x:answermap[x])

# %%
df[(df['Answer']=='no')&(df['Test Example']=='Paraphrasing')]

# %%
for task in tasks:
    if task.id == 108675:
        print(task.news_text)
        print("---")
        print(task.sci_text)
        break
# %%
task.hash
#%%
task.news_text[0:105]
# %%
task.sci_text[830:901]
# %%
task.news_url
# %%
