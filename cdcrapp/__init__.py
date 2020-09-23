import click
import dotenv
import tqdm
import os
import random
import json
import hashlib
import datetime
import pandas as pd
from typing import List, Optional

from tqdm.auto import tqdm

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import Task, UserTask, User, NewsArticle, SciPaper
    
dotenv.load_dotenv()


class CLIContext(object):
    
    def __init__(self):
        self.engine : Engine = create_engine(os.getenv("SQLALCHEMY_DB_URI"))
        self.usersvc : UserService = UserService(self.engine)
        self.tasksvc : TaskService = TaskService(self.engine)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = CLIContext()

@cli.command()
@click.option("--username", type=str, prompt='Provide a username')
@click.option("--email", type=str, prompt='Please provide an email address')
@click.password_option()
@click.pass_obj
def create_user(ctx: CLIContext, username: str, email: str, password: str):
    """Create a new user"""
    
    if ctx.usersvc.get_by_username(username) != None:
        print(f"A user by username {username} already exists. Try another name")
        return

    print(f"Create user with username={username}")
    
    ctx.usersvc.add_user(username, password, email)
  
@cli.command()
@click.option("--username", type=str, prompt='Username')  
@click.option("--frame-button/--no-frame-button", default=False)
@click.option("--admin/--no-admin", default=False)
@click.pass_obj
def set_user_permission(ctx: CLIContext, username: str, frame_button: bool, admin: bool):
    
    user : User = ctx.usersvc.get_by_username(username)
    
    if user is None:
        print(f"Could not find user with username={username}")
        return
    
    print(f"Setting frame_button_visible={frame_button} for {username}")
    print(f"Setting admin={admin} for {username}")
    user.view_gsheets = frame_button
    user.is_admin = admin
    ctx.usersvc.update(user)
    
@cli.command()
@click.option("--username", type=str, prompt='Username')
@click.option("--password", type=str, hide_input=True, prompt='Password:')
@click.pass_obj
def authenticate(ctx: CLIContext, username: str, password: str):
    
    print("login result: ", ctx.usersvc.authenticate(username,password))
    

@cli.command()
@click.option("--username", type=str, prompt='Username')
@click.password_option()
@click.pass_obj
def change_password(ctx: CLIContext, username: str, password: str):
    user : User = ctx.usersvc.get_by_username(username)

    ctx.usersvc.update_password(user, password)
    print("login result: ", ctx.usersvc.authenticate(username,password))

@cli.command()
@click.argument("user_profile", type=click.Path(exists=True))
@click.option("--username", type=str, prompt='User to import data into')
@click.pass_obj
def import_user(ctx: CLIContext, user_profile: str, username: str):
    """Import an existing user profile from legacy CDCR tool and associate with given username"""
    
    # check that the user is valid
    user = ctx.usersvc.get_by_username(username)
    
    if not user:
        print(f"No user found with username={username}")
        return
    
    print(f"Load user work from {user_profile}")
    
    
    with open(user_profile, "r") as f:
        total = sum([1 for line in f])
        f.seek(0)
        
        for line in tqdm(f, total=total):
            
            work = json.loads(line)
            
            task = ctx.tasksvc.get_by_hash(hash=work['hash'])
            
            if not task:
                tqdm.write(f"Could not find task with hash={work['hash']}")
                continue
            
            if work['label'] == "invalid":
                print(f"Mark task with hash={work['hash']} as bad")
                task.is_bad = True
                ctx.tasksvc.update(task)
            
            else:
                
                ctx.usersvc.user_add_task(user,task, work['label'] )
                
                if work.get('iaa', False):
                    print(f"Mark IAA task where hash={work['hash']}")
                    task.is_iaa = True
                    ctx.tasksvc.update(task)

@cli.command()
@click.option("--new-count", type=int, default=150)
@click.pass_obj
def rebalance_iaa(ctx: CLIContext, new_count: int):
    """Rebalance IAA tasks so that new users are not overwhelmed"""
    from cdcrapp.services import TaskService
    from cdcrapp.model import Task

    # get tasks that are IAA

    iaa_tasks = ctx.tasksvc.list(Task, filters={"is_iaa":True})
    iaa_priority = ctx.tasksvc.list(Task, filters={"is_iaa_priority":True})

    print(f"Found {len(iaa_tasks)} tasks marked is_iaa and {len(iaa_priority)} tasks marked is_iaa_priority")
    print("Rebalance priority tasks to max of 150")

    ctx.tasksvc.rebalance_iaa(new_count)

    

@cli.command()
@click.argument("json_file", type=click.Path(exists=False))
@click.argument("output_file", type=click.Path(exists=False))
@click.option('--remove-singletons/--no-remove-singletons', default=False)
@click.pass_obj
def export_conll(ctx: CLIContext, json_file: str, output_file:str, remove_singletons=False):
    """Export tasks to conll format"""

    from cdcrapp.export import export_to_conll

    export_to_conll(json_file, output_file, remove_singletons)

@cli.command()
@click.argument("json_dir", type=click.Path(exists=False))
@click.option("--seed", type=int, default=42)
@click.option("--train-split", type=float, default=0.6)
@click.option("--dev-split", type=float, default=0.2)
@click.option("--exclude-user", type=int, multiple=True )
@click.option("--min-coverage", type=float, default=None)
@click.pass_obj
def export_json(ctx: CLIContext, json_dir:str, seed:int, train_split:float, dev_split:float, exclude_user: List[int], min_coverage: Optional[float]):
    """Export json to conll format"""
    

    t = ctx.tasksvc.get_annotated_tasks(exclude_users=exclude_user, min_coverage=min_coverage)
    
    from cdcrapp.export import export_to_json

    export_to_json(t, json_dir, train_split=train_split, dev_split=dev_split, seed=seed)


    


@cli.command()
@click.argument("pkl_file", type=click.Path(exists=True))
@click.pass_obj
def compare(ctx: CLIContext, pkl_file:str):
    t = ctx.tasksvc.get_annotated_tasks()

    from cdcrapp.compare import compare
    
    for news_id, sci_id, news_ent, sci_ent in compare(pkl_file, t):
        print(news_id, sci_id, news_ent, sci_ent)


@cli.command()
@click.pass_obj
def get_doc_coverage(ctx: CLIContext):
    """Get coverage of news documents"""

    from collections import Counter

    c = Counter()

    for row in ctx.tasksvc.get_task_doc_coverage():
        c[row['complete_percent']] += 1

    print("Percent Complete, Count")
    for percent, count in c.items():
        print(f"{percent}%",count)


@cli.command()
@click.argument("pkl_file", type=click.Path(exists=True))
@click.pass_obj
def import_model_results(ctx: CLIContext, pkl_file:str):
    from cdcrapp.compare import compare
    
    t = ctx.tasksvc.get_annotated_tasks()
    candidates = compare(pkl_file, t)

    with ctx.tasksvc.session() as session:
        
        for news_id, sci_id, news_ent, sci_ent in candidates:

            news_article = session.query(NewsArticle).get(news_id)

            if news_article is None:
                print(f"Failed to find news article {news_id} - skipping...")
                continue

            sci_paper = session.query(SciPaper).get(sci_id)

            if sci_paper is None:
                print(f"Failed to find science paper {sci_id}. Skipping...")
                continue

            task = Task(scipaper=sci_paper, newsarticle=news_article, news_ent=news_ent, sci_ent=sci_ent, priority=5)
            
            task.hash = hashlib.new("sha256", task.news_url.encode() + 
                task.sci_url.encode() + 
                task.news_ent.encode() + 
                task.sci_ent.encode()).hexdigest()

            # try matching the hash
            existing_task = session.query(Task).filter(Task.hash == task.hash).one_or_none()

            # if the hash doesn't match then try to match values 
            if existing_task is None:

                existing_task = session.query(Task).filter(
                    Task.sci_paper_id==sci_id, 
                    Task.news_article_id==news_id, 
                    Task.news_ent==news_ent, 
                    Task.sci_ent==sci_ent).one_or_none()

            if existing_task:
                existing_task.priorty=5
                print(f"Update priority for task {existing_task.hash}")
            else:
                session.add(task)
                print(f"Add new task {task.hash}")


@cli.command()
@click.argument("json_dir", type=click.Path(exists=True))
@click.argument("csvname", type=click.Path(exists=False, file_okay=True))
def export_doc_contents(json_dir, csvname):
    """Return the total number of individual documents in exported corpus"""

    from .export import export_json_to_csv

    export_json_to_csv(json_dir, csvname)


@cli.command()
@click.argument("json_dir", type=click.Path(exists=True))
def count_docs(json_dir):
    """Return the total number of individual documents in exported corpus"""

    test_file = os.path.join(json_dir,"test.json")
    train_file = os.path.join(json_dir,"train.json")
    dev_file = os.path.join(json_dir,"dev.json")

    total_docs = 0
    for file in [test_file,train_file,dev_file]:
        with open(file) as f:
            docs = json.load(f)
            print(f"Found {len(docs)} docs in {file}")
            total_docs += len(docs)

    print(f"Total entities: {total_docs}")

@cli.command()
@click.argument("json_dir", type=click.Path(exists=True))
def count_mentions(json_dir):
    """Return the total number of counts in the exported corpus"""

    test_file = os.path.join(json_dir,"test_entities.json")
    train_file = os.path.join(json_dir,"train_entities.json")
    dev_file = os.path.join(json_dir,"dev_entities.json")

    total_ents = 0
    for file in [test_file,train_file,dev_file]:
        with open(file) as f:
            ents = json.load(f)
            print(f"Found {len(ents)} entities in {file}")
            total_ents += len(ents)

    print(f"Total entities: {total_ents}")

@cli.command()
@click.argument("json_dir", type=click.Path(exists=True))
def count_clusters(json_dir):
    """Return the total number of counts in the exported corpus"""

    from collections import Counter

    test_file = os.path.join(json_dir,"test_entities.json")
    train_file = os.path.join(json_dir,"train_entities.json")
    dev_file = os.path.join(json_dir,"dev_entities.json")

    
    total_ents = 0
    for file in [test_file,train_file,dev_file]:
        cluster_ids = []
        with open(file) as f:
            ents = json.load(f)
            for ent in ents:
                cluster_ids.append(ent['cluster_id'])

            cids = Counter(cluster_ids)

            non_singletons = [id for (id,count) in cids.items() if count > 1]
            singletons = [id for (id,count) in cids.items() if count == 1]
            print(f"Found {len(non_singletons)} clusters in {file}")
            print(f"Found {len(singletons)} singletons in {file}")
            total_ents += len(ents)

    print(f"Total entities: {total_ents}")

@cli.command()
@click.argument("corpus_dir", type=click.Path(exists=True, dir_okay=True))
@click.option("--priority", type=int, default=5)
@click.pass_obj
def prioritise_docs(ctx: CLIContext,corpus_dir: str, priority=5):
    """Re-prioritise tasks in documents associated with the given json corpus"""

    for fn in ['dev.json','train.json','test.json']:

        news_docs = []
        sci_docs = []

        with open(os.path.join(corpus_dir, fn),'r') as f:
            docs = json.load(f)

            docnames = docs.keys()

            for doc in docnames:
                topic,doctype,docid = doc.split("_")

                if doctype == "news":
                    news_docs.append(int(docid))
                else:
                    sci_docs.append(int(docid))

    print(f"Found {len(news_docs)} news docs and {len(sci_docs)} sci docs.")

    with ctx.tasksvc.session() as session:
        changes = session.query(Task)\
          .filter(Task.news_article_id.in_(news_docs) | Task.sci_paper_id.in_(sci_docs))\
          .update({"priority": priority}, synchronize_session=False)
        print(f"Updated {changes} rows")
        session.commit()


    




@cli.command()
@click.argument("json_file", type=click.Path(exists=False))
@click.option("--seed", type=int, default=42)
@click.option("--train-split", type=float, default=0.6)
@click.option("--dev-split", type=float, default=0.2)
@click.pass_obj
def export_joshi(ctx: CLIContext, json_file:str, seed:int, train_split:float, dev_split:float):
    t = ctx.tasksvc.get_annotated_tasks()

    from .export import export_to_joshi

    export_to_joshi(t, json_file, train_split, dev_split, seed)

@cli.command()
@click.argument("sheet_id", type=str)
@click.argument("sheet_range", type=str)
@click.pass_obj
def import_difficult_tasks(ctx: CLIContext, sheet_id: str, sheet_range:str):
    """Get difficult tasks from google sheets and update in db"""

    from cdcrapp.gsheets import Spreadsheet

    sheet = Spreadsheet(sheet_id)
    sheet.connect()

    with ctx.tasksvc.session() as session:
        for hash,username,_ in sheet.get_range(sheet_range)['values']:
            user = session.query(User).filter(User.username==username.strip().lower()).one_or_none()

            if user is None:
                print(f"Could not find user {username.strip().lower()} skipping task...")
                continue
            
            task = session.query(Task).filter(Task.hash==hash).one_or_none()

            if task is None:
                print(f"Could not find task with hash {hash}. Skipping task...")
                continue

            task.is_difficult = True
            task.is_difficult_user = user
            task.is_difficult_reported_at = datetime.datetime.utcnow()

        session.commit()



@cli.command()
@click.argument("task_csv", type=click.Path(exists=True))
@click.pass_obj
def import_tasks(ctx: CLIContext, task_csv: str):
    """Import annotation tasks from a CSV"""
    df = pd.read_csv(task_csv)
    
    from cdcrapp.services import TaskService
    from cdcrapp.model import Task
    
    
    print(f"Found {len(df)} tasks in f{task_csv}...")
    print(f"Adding tasks to database")
    
    engine = create_engine(os.getenv("SQLALCHEMY_DB_URI"))
    taskmgr = TaskService(engine)
    
    # filter existing tasks
    tasks: List[Task] = taskmgr.list(Task)
    
    existing = set([t.hash for t in tasks])
    
    not_ingested = df[~df.hash.isin(existing)]
    
    tasks = []
    for i, row in tqdm(not_ingested.iterrows(), total=len(not_ingested)):
        task = Task(hash=row['hash'],
                    news_ent=row['News Candidates'], 
                    sci_ent=row['Abstract Candidates'],
                    news_url=row['URL'][:255],
                    sci_url=row['doi'],
                    news_text=row['Summary'],
                    sci_text = row['abstract'],
                    similarity = row['bert_similarity']
                    )
        
        tasks.append(task)
        
        if i % 1000 == 0:
            taskmgr.add_tasks(tasks)
            tasks = []
    
    print("Import complete")

@cli.command()
@click.pass_obj        
def tidy_duplicate_tasks(ctx: CLIContext):
    """Remove duplicate tasks"""
    from sqlalchemy import desc
    from sqlalchemy.sql.functions import count

    with ctx.tasksvc.session() as session:
        q = session.query(count(Task.hash).label('total'), Task.news_article_id, Task.sci_paper_id, Task.news_ent, Task.sci_ent)\
              .group_by(Task.news_article_id, Task.sci_paper_id, Task.news_ent, Task.sci_ent).order_by(desc('total'))

        for total, news_id, sci_id, news_ent, sci_ent in q.all():
            
            # We're sorted in descending order by total and we only
            # care about dupes so break when we get to 1
            if total < 2:
                break

            # we should end up with the most important task at the top (e.g. IAA tasks or recently created ones)
            tasks = session.query(Task)\
                .filter(Task.news_article_id==news_id, Task.sci_paper_id==sci_id, Task.sci_ent==sci_ent, Task.news_ent==news_ent)\
                    .order_by(Task.is_iaa.desc(), Task.created_at.desc()).all()

            deleted_one = False
            for task in tasks:
                if len(task.usertasks) < 1:
                    print(f"Remove duplicate task {task.id}")
                    session.delete(task)
                    deleted_one = True
                    break
            
            if not deleted_one:
                print(f"Was unable to delete a task for {news_id},{sci_id},{news_ent},{sci_ent}")
                print(f"Move all links from {tasks[-1].id} -> {tasks[0].id}")

                existing_uts = set()
                for ut in tasks[0].usertasks:
                    existing_uts.add((ut.user_id,ut.task_id))

                for ut in tasks[-1].usertasks:
                    if (ut.user_id, tasks[0].id) in existing_uts:
                        print(f"Remove duplicate UT {ut.user_id},{ut.task_id}")
                        session.delete(ut)
                    else:
                        print(f"Move UT from task {ut.task_id} to {tasks[0].id}")
                        ut.task_id = tasks[0].id
                        existing_uts.add((ut.user_id, tasks[0].id))

            

        session.commit()


if __name__ == "__main__":
    cli() #pylint: disable=no-value-for-parameter