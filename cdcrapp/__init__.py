import click
import dotenv
import tqdm
import os
import random
import json
import hashlib
import pandas as pd
from typing import List

from tqdm.auto import tqdm

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import Task, UserTask, User
    
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
@click.pass_obj
def export_conll(ctx: CLIContext, json_file: str, output_file:str):
    """Export tasks to conll format"""

    from cdcrapp.export import export_to_conll

    export_to_conll(json_file, output_file)

@cli.command()
@click.argument("json_file", type=click.Path(exists=False))
@click.option("--seed", type=int, default=42)
@click.option("--split", type=float, default=0.7)
@click.pass_obj
def export_json(ctx: CLIContext, json_file:str, seed:int, split:float):
    """Export json to conll format"""
    t = ctx.tasksvc.get_annotated_tasks()

    from cdcrapp.export import export_to_json

    export_to_json(t, json_file, split=split, seed=seed)


@cli.command()
@click.argument("pkl_file", type=click.Path(exists=True))
@click.pass_obj
def compare(ctx: CLIContext, pkl_file:str):
    t = ctx.tasksvc.get_annotated_tasks()

    from cdcrapp.compare import compare
    
    compare(pkl_file, t)


@cli.command()
@click.argument("pkl_file", type=click.Path(exists=True))
@click.pass_obj
def import_model_results(ctx: CLIContext, pkl_file:str):
    from cdcrapp.compare import compare
    
    t = ctx.tasksvc.get_annotated_tasks()
    candidates = compare(pkl_file, t)

    

    with ctx.tasksvc.session() as session:
        for news_id, sci_id, news_ent, sci_ent in candidates:
            task = Task(news_article_id=news_id,sci_paper_id=sci_id, news_ent=news_ent, sci_ent=sci_ent, priority=5)
            session.add(task)
            task.hash = hashlib.new("sha256", task.news_url.encode() + 
                task.sci_url.encode() + 
                task.news_ent.encode() + 
                task.sci_ent.encode()).hexdigest()

            print(task.hash)




@cli.command()
@click.argument("json_file", type=click.Path(exists=False))
@click.option("--seed", type=int, default=42)
@click.option("--split", type=float, default=0.7)
@click.pass_obj
def export_joshi(ctx: CLIContext, json_file:str, seed:int, split:float):
    t = ctx.tasksvc.get_annotated_tasks()

    from .export import export_to_joshi

    export_to_joshi(t, json_file, split, seed)


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
        
        

if __name__ == "__main__":
    cli() #pylint: disable=no-value-for-parameter