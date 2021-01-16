#%% 
import json
import hashlib
from dotenv import load_dotenv
from sqlalchemy import create_engine
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import Task, NewsArticle, SciPaper

def get_sql_engine():
    return create_engine(os.getenv("SQLALCHEMY_DB_URI"))

load_dotenv()
_engine = get_sql_engine()
_usersvc : UserService = UserService(_engine)
_tasksvc : TaskService = TaskService(_engine)
# %%
sci_docs = []
news_docs = []

for seg in ['dev','test','train']:
    with open(f"../mentions/31_07_20_5pc/{seg}_entities.json") as f:
        data = json.load(f)

    for ent in data:
        _, doc_type, doc_id =  ent['doc_id'].split("_")

        if doc_type == 'science':
            sci_docs.append(int(doc_id))
        else:
            news_docs.append(int(doc_id))

# %%
news_docs = set(news_docs)
sci_docs = set(sci_docs)
# %%
news_docs

# %%
news_urls = {}
with _usersvc.session() as session:
    news_articles = session.query(NewsArticle).filter(NewsArticle.id.in_(news_docs)).all()

    for article in news_articles:
        news_urls[article.id] = {
            "url": article.url, 
            "sha256": hashlib.new('sha256', 
            article.summary.encode('utf8')).hexdigest()
        }
# %%
with open("news_urls.json", 'w') as f:
    json.dump(news_urls, f, indent=2)
# %%
with _usersvc.session() as session:
    sci_papers = session.query(SciPaper).filter(SciPaper.id.in_(sci_docs)).all()

    sci_json = {}

    for paper in sci_papers:
        sci_json[paper.id] = {"doi": paper.url, "abstract": paper.abstract}
# %%
with open("sci_papers.json", 'w') as f:
    json.dump(sci_json, f, indent=2)
# %%
