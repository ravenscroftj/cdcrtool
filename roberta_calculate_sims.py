"""Extract completed tasks from CDCR database and calculate roberta embeddings
"""
#%%
import json
import hashlib
import os
import sqlalchemy
import csv

from tqdm.auto import tqdm
from dotenv import load_dotenv
from sqlalchemy import create_engine
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import Task, NewsArticle, SciPaper, UserTask

# %%

def get_sql_engine():
    return create_engine(os.getenv("SQLALCHEMY_DB_URI"))


load_dotenv()
_engine = get_sql_engine()
_usersvc : UserService = UserService(_engine)
_tasksvc : TaskService = TaskService(_engine)


# %%
# collect sets of documents that our task should be limited to
# the 'definitive' CD^2CR corpus is from 31/7/20
sci_docs = []
news_docs = []

for seg in ['dev','test','train']:
    with open(f"mentions/31_07_20_5pc/{seg}_entities.json") as f:
        data = json.load(f)

    for ent in data:
        _, doc_type, doc_id =  ent['doc_id'].split("_")

        if doc_type == 'science':
            sci_docs.append(int(doc_id))
        else:
            news_docs.append(int(doc_id))
#%%
# create a set of IDs for news and science docs respectively
news_docs = set(news_docs)
sci_docs = set(sci_docs)

#%%
news_docs

rows = []


with _usersvc.session() as session:

    print("Selecting tasks...")
    tasks = session.query(Task)\
        .filter(Task.news_article_id.in_(news_docs) | Task.sci_paper_id.in_(sci_docs))\
        .filter(Task.id.in_(session.query(sqlalchemy.distinct(UserTask.task_id))))\
        .all()

    with open("task_dump.csv",'w') as f:

        csvw = csv.DictWriter(f, fieldnames=['id','hash','news_text','sci_text','news_ent','sci_ent','bert_similarity'])

        csvw.writeheader()

        for task in tqdm(tasks):
            csvw.writerow({
                "id": task.id, 
                "hash": task.hash,
                "news_text": task.news_text, 
                "sci_text": task.sci_text,
                "news_ent": task.news_ent,
                "sci_ent": task.sci_ent,
                "bert_similarity": task.similarity,
            })

#%%
len(tasks)

#%%

#%%
from transformers import RobertaModel, RobertaTokenizerFast

model = RobertaModel.from_pretrained("roberta-large")
transformer = RobertaTokenizerFast.from_pretrained("roberta-large")

# %%
import pandas as pd

df = pd.read_csv("roberta_sim.csv")

df.head()
# %%
df2 = pd.read_csv("../news-bias-detection/summaries.csv.zip")
# %%
df2
# %%
len(df)
# %%
