import os
import json
import numpy as np
import pandas as pd
import streamlit as st 
import hashlib
import redis
import re
from dotenv import load_dotenv

from typing import Optional

from sqlalchemy import create_engine

from cdcrapp.gsheets import Spreadsheet
from cdcrapp.services import UserService, TaskService
from cdcrapp.model import User, Task, UserTask

load_dotenv()

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
        
        self.user = None
        self.redis = get_redis_connection()
        self.last_task_id = None

    def init_ui(self):

        st.sidebar.header("User Profile")
        user_selector = st.sidebar.selectbox("User:", options=self.user_list())
        user_password = st.sidebar.text_input("Password", type="password")
        
        if user_selector == "---":
            self.show_front_page()
        
        
        if not _usersvc.authenticate(user_selector, user_password):
            st.header("Log in")
            st.write("please provide the password now")
        
        else:
            
            self.user = self.get_user_profile(user_selector)
            
            self.info_ph = st.sidebar.empty()
            
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
            
    def connect_buttons(self):
            self.yes_btn = self.yes_btn_ph.button("Yes")
            self.no_btn = self.no_btn_ph.button("No")
            self.report_btn = self.report_btn_ph.button("Report Bad Task (Never see again)")
            
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
        print("handle task outcome")
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
            if np.random.random() < float(os.getenv('IAA_RATIO', 0.3)) and (not task.is_iaa):
                task.is_iaa = True
            
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
        
        task : Task = _tasksvc.next_tasks_for_user(self.user)
        
        self.update_progress()
        
        next_task : Optional[Task] = self.manage_task_navigation()
        
        if next_task is not None:
            
            self.show_task_spreadsheet_options(next_task)
            self.handle_sheet_updates(next_task)

            try:
                entity, start, end = next_task.news_ent.split(";")
                
                buffer = next_task.news_text[:int(start)].strip() + " **" + entity + "** " + next_task.news_text[int(end):].strip()
                
                sci_entity, start, end = next_task.sci_ent.split(";")
                
                abstract = next_task.sci_text.replace("\s+"," ")
                
                sci_buffer = next_task.sci_text[:int(start)].strip() + " **" + sci_entity + "** " + next_task.sci_text[int(end):].strip()
                
                self.task_question_ph.markdown(f"## Are *'{entity}'* and *'{sci_entity}'* mentions of the same thing?")
                

            except ValueError:
                
                st.markdown("There was a problem with this task. Click Report to continue.")
            
            #skip = st.button("Skip (you will see this again)")
            sci_buffer = re.sub("^\s+","\n", sci_buffer, flags=re.MULTILINE)
        
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


        
    def add_user(self, username):
        user_file = os.path.join(DATA_DIR, "users.json")
        
        users = []
        
        if os.path.exists(user_file):
            with open(user_file) as f:
                users = json.load(f)
                
        users.append({"name": username})

        with open(user_file,'w') as f:
            json.dump(users, f)
            
    def get_user_profile(self, username) -> User:
        return _usersvc.get_by_username(username)
        

    def show_front_page(self):
        
        with open(os.path.join(ASSETS_DIR, "README.md")) as f:
            st.markdown(body=f.read())
            
        st.markdown("**If you are a returning user, select your username in the sidebar. Otherwise contact [James](twitter.com/jamesravey/) if you would like to get involved.**")
        
        # username = st.text_input("Enter a username:")
        # password = st.text_input("Enter a password:", type="password")
        # conf_pw  = st.text_input("Confirm password:", type="password")
        
        # cb = st.button("Create a user profile")
        
        # if cb:
        #     self.add_user(username)
        #     st.write("Thank you for creating a new user... Please refresh your browser to log in.")
        

    def append_user_work(self, username, work):
        data_file = os.path.join(DATA_DIR, f"user_{username}.jsonl")
        
        with open(data_file, "a") as f:
            f.write(json.dumps(work) + "\n")

    def taskhash(self, row):
        h = hashlib.new("sha256", row['URL'] + row['DOI'] + row['News Candidates'] + row['Abstract Candidates'])
        return h.hexdigest()


            
app = CDCRTool()
app.init_ui()

