import os
import json
import numpy as np
import pandas as pd
import streamlit as st 
import hashlib
import redis
import re
from dotenv import load_dotenv

import matplotlib.pyplot as plt
import seaborn as sns

from typing import Optional

from sqlalchemy import create_engine

from cdcrapp.gsheets import Spreadsheet
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import User, Task, UserTask, NewsArticle, SciPaper

load_dotenv()

sns.set_style()

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 200)

pd.options.display.max_colwidth = 200


@st.cache(allow_output_mutation=True)
def get_sql_engine():
    return create_engine(os.getenv("SQLALCHEMY_DB_URI"))

_engine = get_sql_engine()
_usersvc : UserService = UserService(_engine)
_tasksvc : TaskService = TaskService(_engine)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../assets/")

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

INTERESTING_RANGE = os.environ.get("INTERESTING_RANGE")
FRAME_RANGE = os.environ.get("FRAME_RANGE")

SECRET = os.environ.get("SECRET")


IAA_GUIDE = """## Interpretation of Kappa Scores (Applicable to Fleiss and Cohen scores)
&lt0 - no agreement\n
0-0.20 slight agreement\n
0.21-0.40 fair agreement\n
0.41-0.6 moderate agreement\n
0.61-0.80 substantial agreement\n
0.81 - 1.0 almost perfect agreement"""


@st.cache(allow_output_mutation=True)
def get_spreadsheet_client():
    sheet = Spreadsheet(spreadsheet_id=SPREADSHEET_ID)
    sheet.connect()
    
    return sheet

@st.cache(hash_funcs={redis.Redis: id})
def get_redis_connection():
    return redis.Redis(host=os.getenv("REDIS_SERVER", "localhost"), port=6379, password=os.getenv("REDIS_PASSWORD"))

@st.cache(allow_output_mutation=True)
def get_interesting_tasks():
    """Get all interesting/difficult tasks from google sheets"""
    all_complete = dict()
    sheet = get_spreadsheet_client()
    for (hash, user, _) in sheet.get_range(INTERESTING_RANGE)['values']:
        all_complete[hash.strip()] = user
    
    return all_complete

@st.cache(allow_output_mutation=True)
def get_frame_tasks():
    """Get all tasks with an interesting frame from google sheets"""
    all_complete = dict()
    sheet = get_spreadsheet_client()
    
    for (hash, user) in sheet.get_range(FRAME_RANGE)['values']:
        all_complete[hash.strip()] = user
    
    return all_complete

class CDCRTool():

    def __init__(self):
        self.yes_btn = None
        self.no_btn = None
        self.report_btn = None
        self.interesting_btn = None
        self.frame_btn = None
        self.sheet = Spreadsheet(SPREADSHEET_ID)
        
        self.user : User = None
        self.redis = get_redis_connection()
        self.last_task_id = None

    def init_ui(self):

        st.sidebar.header(body="User Profile")
        user_selector = st.sidebar.selectbox(label="User:", options=self.user_list())
        user_password = st.sidebar.text_input(label="Password", type="password")
        
        if user_selector == "---":
            self.show_front_page()
        
        
        if not _usersvc.authenticate(user_selector, user_password):
            st.header("Log in")
            st.write("please provide the password now")
            
        
        else:
            
            self.user = self.get_user_profile(user_selector)
            
            self.info_ph = st.sidebar.empty()
            show_admin = False
            
            if self.user.is_admin:
                show_admin = st.sidebar.checkbox("Toggle Admin View")

            
            if show_admin:
                self.display_admin_panel()
            else:            
                self.nav_header_ph = st.sidebar.empty()
                self.task_id_ph = st.sidebar.empty()
                self.task_decide_ph = st.sidebar.empty()
                self.task_decide = self.task_decide_ph.radio('Current task', ['random', 'from Task ID'])
                
                self.task_question_ph = st.empty()
                
                st.markdown("Use the below button to add this task to the 'difficult' list. You need to do this before you give a Yes/No/Report answer if applicable.")
                self.interesting_btn_ph = st.empty()
                self.frame_btn_ph = st.empty()
                
                st.markdown("Use the buttons below to give a final Yes/No/Report answer")
                self.yes_btn_ph = st.empty()
                self.no_btn_ph = st.empty()
                self.report_btn_ph = st.empty()
                
                
                # set up task buttons
                self.connect_buttons()
                
                self.task_markdown_ph = st.empty()
                
                #process any work (via redis)
                self.handle_task_outcome()
                
                self.show_task() 
            
    def display_admin_panel(self):
        
        st.markdown("# Admin View")
        
        # get user performance
        
        progress = _usersvc.get_all_user_progress()
        
        df = pd.DataFrame.from_records(progress, columns=['User','Completed Examples'])

        
        st.markdown("## Total Tasks")
        
        st.dataframe(df)

        # get task difficulty
        diffdist = _tasksvc.get_task_difficulty_dist()
        
        sns.distplot(diffdist)

        st.markdown("### Total distinct answers")


        dists_df = pd.DataFrame(data=_tasksvc.get_answer_dists(), columns=['Answer', 'Count'])
        st.dataframe(dists_df)

        st.markdown("### BERT Similarity distribution of Tasks")
        st.pyplot()



        st.markdown("## User Statistics")

        user_stats = pd.DataFrame(data=_usersvc.get_user_statistics(), columns=['Username', 'yes', 'no'])

        st.dataframe(user_stats)

        st.markdown("## Multi Annotator IAA (Fleiss' Kappa)")

        iaa_table = pd.DataFrame(data=_usersvc.get_fleiss_iaa(), columns=['Group', 'Samples', 'Fleiss IAA Score'])
        
        st.dataframe(iaa_table)

        
        st.markdown("## Pairwise IAA (Cohen's Kappa) \n\nSelect users to compare")

        
        users = self.user_list()
        
        username_a = st.selectbox(label="User A", options=users)
        username_b = st.selectbox(label="User B", options=users)
        
        if username_a != "---" and username_b != "---":
            
            if username_a == username_b:
                st.markdown("You can't compare the user against themselves")
            else:
            
                iaa = _usersvc.get_pairwise_iaa(username_a,username_b)
            
                st.markdown(f"IAA {username_a} <-> {username_b}: {iaa}")        
        
                
        st.markdown(IAA_GUIDE)


        st.markdown("## Bad Tasks")

        bad_tasks = _tasksvc.list(Task, filters={"is_bad": True}, joins=[NewsArticle, SciPaper])


        rows = []
        for task in bad_tasks:
            rows.append({
                "hash": task.hash,
                "news_url": task.newsarticle.url,
                "sci_url": task.scipaper.url
            })

        df = pd.DataFrame.from_records(rows)

        st.dataframe(df)

        st.markdown("## Bad Task Finder \n Enter task hash to find other news articles and scientific papers that share the same ")

        bad_filter = st.text_input(label="Hash")

        if bad_filter != "":
            task = _tasksvc.get_by_hash(bad_filter, allow_wildcard=True)

            if task is None:
                st.markdown("Sorry, no task with that hash could be found")
            else:
                st.markdown("********")
                st.markdown(f"Hash: {task.hash} \n\n News URL: {task.news_url} \n\n Science DOI: http://dx.doi.org/{task.sci_url}\n\n")
                st.markdown(f"News Ent: {task.news_ent.split(';')[0]} \n\n Sci Ent: {task.sci_ent.split(';')[0]}\n")
                st.markdown(f"News Text: {task.news_text} \n\n Science Text: {task.sci_text}")
                st.markdown("## Danger Zone")

                block_article_btn = st.button(label="Remove all tasks combining these articles")

                if block_article_btn:

                    _tasksvc.remove_tasks_by_doc_ids(task.news_article_id, task.sci_paper_id)

                    st.markdown("Removed the task.")



            
    def connect_buttons(self):
            self.yes_btn = self.yes_btn_ph.button("Yes")
            self.no_btn = self.no_btn_ph.button("No")
            self.report_btn = self.report_btn_ph.button("Bad Example")
            
    def handle_sheet_updates(self, task):
            
        if self.interesting_btn:
            self.add_interesting_task(task)
            self.interesting_btn_ph.markdown("**This task has been added to the 'interesting' spreadsheet.**")
            
        if self.frame_btn:
            self.add_frame_task(task)
            self.frame_btn_ph.markdown("**This task has been added to the 'frame tasks' spreadsheet.**")

    def add_frame_task(self, task):
        self.add_sheet_task(task, FRAME_RANGE)
        #append to cache
        get_frame_tasks()[task.hash] = self.user.username

    def add_interesting_task(self, task):
        self.add_sheet_task(task, INTERESTING_RANGE)
        #append to cache
        get_interesting_tasks()[task.hash] = self.user.username
        
    def add_sheet_task(self, task: Task, range):
        # generate text
        entity = task.news_ent.split(";")[0]
        sci_entity = task.sci_ent.split(";")[0]
        comment = f"{entity} and {sci_entity}"
        
        #append to actual sheet
        sheet = get_spreadsheet_client()
        row = [task.hash, self.user.username, comment]
        sheet.append_sheet(range, [row])

            
    def handle_task_outcome(self):
        if self.yes_btn or self.no_btn or self.report_btn:
            
            if self.redis.get(f"user_{self.user.id}_task_id") is not None:
                self.last_task_id =  self.redis.get(f"user_{self.user.id}_task_id").decode("utf8")
                print(f"Last task id={self.last_task_id}")
            
            if self.last_task_id is None:
                st.error("You clicked OK but I couldn't find the task in redis...")
                return
            
            task : Task = _tasksvc.get_by_hash(self.last_task_id)
            
            if self.report_btn:
                print(f"Report task is bad {task.hash}")
                task.is_bad = True
                _tasksvc.update(task)
                return
            
            # there is a random chance that this will become an IAA task
            if np.random.random() < float(os.getenv('IAA_RATIO', 0.05)) and (not task.is_iaa):
                task.is_iaa = True
                task.is_iaa_priority = True
            
            if self.yes_btn:
                lbl = 'yes'
            elif self.no_btn:
                lbl = 'no'

            print(f"Add user task user={self.user.username}, task={task.hash}")
            #write exercise to cache
            _usersvc.user_add_task(self.user, task, lbl)
            

            
    def update_progress(self):
        
        self.info_ph.markdown("You have done {} tasks! Hooray!".format(_usersvc.get_progress_for_user(self.user)))
            
    def manage_task_navigation(self):
        
        self.nav_header_ph.header("Task Navigation")
        
        

        next_task = None
        
        if self.task_decide =='random':
            next_task = _tasksvc.next_tasks_for_user(self.user)
            task_id = self.task_id_ph.text_input('Task Id (Magic ID you can use to find this task again)', value=next_task.hash)
            
        elif self.task_decide == 'from Task ID':
            
            task_id = self.task_id_ph.text_input('Task Id (Magic ID you can use to find this task again)', value='')
            if task_id != '':
                next_task = _tasksvc.get_by_hash(task_id)
            else:
                st.markdown("# Please enter a task ID to navigate to it\n\n A task ID is a SHA hash like `bf4f745552980203a2a2b6e641b0c069141c7f8e2f9f81466fa112c59e9a1274`")
        
        self.last_task_id =  self.redis.set(f"user_{self.user.id}_task_id", task_id)
        
        return next_task


    def show_task(self):
        
        self.update_progress()
        
        next_task : Optional[Task] = self.manage_task_navigation()
        
        if next_task is not None:
            
            self.show_task_spreadsheet_options(next_task)
            self.handle_sheet_updates(next_task)

            try:
                entity, start, end = next_task.news_ent.split(";")
                
                buffer = next_task.news_text[:int(start)].strip() + " **" + entity + "** " + next_task.news_text[int(end):].strip()
                
                sci_entity, start, end = next_task.sci_ent.split(";")
                
                sci_buffer = next_task.sci_text[:int(start)].strip() + " **" + sci_entity + "** " + next_task.sci_text[int(end):].strip()
                
                self.task_question_ph.markdown(f"## Are *'{entity}'* and *'{sci_entity}'* mentions of the same thing?")
                

            except ValueError:
                
                st.markdown("There was a problem with this task. Click Report to continue.")
            
            #skip = st.button("Skip (you will see this again)")
            sci_buffer = re.sub(r"^\s+","\n", sci_buffer, flags=re.MULTILINE)
        
            self.task_markdown_ph.markdown(f"## News Summary [[link]]({next_task.news_url})\n" 
                        + buffer 
                        + f"\n\n\n## Science Abstract [[link]](https://dx.doi.org/{next_task.sci_url})\n" 
                        + sci_buffer.strip())
            
            
    
    def show_task_spreadsheet_options(self, task: Task):
        
        if task.hash not in get_interesting_tasks():
            self.interesting_btn = self.interesting_btn_ph.button("This task is difficult to think about")
        else:
            self.interesting_btn_ph.markdown(f"**Task already in 'difficult list', added by {get_interesting_tasks()[task.hash]}**")
            
        if self.user.view_gsheets:
            if task.hash not in get_frame_tasks():
                self.frame_btn = self.frame_btn_ph.button("Interesting Frame (Append Spreadsheet)")
            else:
                self.frame_btn_ph.markdown(f"**Task already exists in frame list, added by {get_frame_tasks()[task.hash]}**")


    def user_list(self):
        
        options = ["---"] + [user.username for user in _usersvc.list(User)]
                
        return options 

            
    def get_user_profile(self, username) -> User:
        return _usersvc.get_by_username(username)
        

    def show_front_page(self):
        
        with open(os.path.join(ASSETS_DIR, "README.md")) as f:
            st.markdown(body=f.read())
            
        st.markdown("**If you are a returning user, select your username in the sidebar. Otherwise contact [James](twitter.com/jamesravey/) if you would like to get involved.**")
        

    def taskhash(self, row):
        h = hashlib.new("sha256", row['URL'] + row['DOI'] + row['News Candidates'] + row['Abstract Candidates'])
        return h.hexdigest()


            
app = CDCRTool()
app.init_ui()

