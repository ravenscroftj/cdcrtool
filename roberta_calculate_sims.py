"""Extract completed tasks from CDCR database and calculate roberta embeddings
"""
#%%
import json
import hashlib
import os
import sqlalchemy
import csv
import pandas as pd
import torch

from transformers import RobertaModel, RobertaTokenizerFast
from html import unescape

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

# *************************************************************************
#  In this next section we actually run the RoBERTa experiments
# *************************************************************************


#%%


df = pd.read_csv("task_dump.csv")
# user generated task entries don't have a bert similarity 
# so we exclude them from comparison for now
df.dropna(subset=['bert_similarity'],inplace=True)

#%%

device = torch.device('cuda:0')

model = RobertaModel.from_pretrained("roberta-large").to(device)
tokenizer = RobertaTokenizerFast.from_pretrained("roberta-large")

#%%
def get_tokens_by_offset(start:int,end:int, model_inputs: dict, second_doc=False, sep_char='[SEP]'):
    """Utility function maps character offsets onto roberta or bert subword tokens"""
    tokens = tokenizer.convert_ids_to_tokens(model_inputs['input_ids'])

    found_sep = False
    last_end = 0
    for i, (tok, bounds) in enumerate(zip(tokens, model_inputs['offset_mapping'])):

        if tok == sep_char:
            found_sep = True
        
        if bounds is None:
            continue
            
        if second_doc and not found_sep:
            continue
            
        s,e = bounds#[0]-last_end, bounds[1]-last_end


        if s >= end:
            break
    
        if s >= start:
            yield i,tok

# %%
model_input

# %%
res = model(input_ids=torch.tensor([model_input['input_ids']]).cuda(), attention_mask = torch.tensor([model_input['attention_mask']]).cuda(),output_hidden_states=True)

res.last_hidden_state
# %%
news_tokens
# %%
res.last_hidden_state[0,news_tokens].mean(dim=0).cpu().shape


#%%
input_cache= {}
cache = {}
sim_column_name = 'roberta_similarity'
df[sim_column_name] = pd.NA
sim_column =  df.columns.get_loc(sim_column_name)

df[sim_column] = pd.NA

#%%

for line in tqdm(range(len(df))):

    if (len(df.iloc[line].news_text.strip()) < 1) or (len(df.iloc[line].sci_text.strip()) < 1) :
        continue

    task_hash = df.iloc[line].news_text + df.iloc[line].sci_text

    if task_hash not in input_cache:
        input_cache[task_hash] = tokenizer.encode_plus(text=df.iloc[line].news_text,
            text_pair=df.iloc[line].sci_text,
            max_length=512,
            truncation='only_second',
            add_special_tokens=True,
            pad_to_max_length=True, 
            return_offsets_mapping=True)

    model_input = input_cache[task_hash]

    try:
        news_offset = unescape(df.iloc[line].news_ent).split(";")[1:]
        news_start = int(news_offset[0])
        news_end = int(news_offset[1])

        sci_offset = unescape(df.iloc[line].sci_ent).split(";")[1:]
        sci_start = int(sci_offset[0])# + len(df.iloc[line].summary)
        sci_end = int(sci_offset[1])#+ len(df.iloc[line].summary)

        news_tokens,news_text = zip(*get_tokens_by_offset(news_start,news_end, model_input,False,sep_char=tokenizer.sep_token ))
        sci_tokens, sci_text= zip(*get_tokens_by_offset(sci_start,sci_end, model_input,True,sep_char=tokenizer.sep_token ))
    except ValueError:
        print(line)
        continue
    
    

    if task_hash not in cache:

        with torch.no_grad():
                r = model(
                    input_ids=torch.tensor([model_input['input_ids']]).cuda(), 
                    attention_mask = torch.tensor([model_input['attention_mask']]).cuda(),
                )
        # r.last_hidden_state

        cache[task_hash] = r.last_hidden_state

    news_embedding = cache[task_hash][0,news_tokens].mean(dim=0).cpu()
    sci_embedding = cache[task_hash][0,sci_tokens].mean(dim=0).cpu()

    from scipy.spatial.distance import cosine

    sim = 1 - cosine(news_embedding, sci_embedding)
    df.iloc[line, sim_column ] = sim
    #print(line, df.iloc[line].news_ent, df.iloc[line].sci_ent, sim, df.iloc[line].similarity)


# %%
import pandas as pd
import seaborn as sns

from matplotlib import pyplot as plt

df.dropna(subset=['roberta_similarity'], inplace=True)

line = sns.distplot(df.roberta_similarity, kde=False, label="RoBERTa")
line2 = sns.distplot(df.bert_similarity, kde=False, label="BERT")


plt.legend()
# %%
df.iloc[0]
# %%
