import os
import json
import numpy as np
import pandas as pd
import streamlit as st 
import hashlib
import redis
import re
from dotenv import load_dotenv

from .gsheets import Spreadsheet

load_dotenv()

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../assets/")

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data/CDCRTool")

SPREADSHEET_ID = "1qyC-mv6Z5e74wAxWikI1_MB8hbJbWwxiztD9YJPcWt4"

INTERESTING_RANGE = "Interesting/Difficult Tasks!A1:C"
FRAME_RANGE = "Task Frames!A2:C"

SECRET = "topsecret123"

def get_users():
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    user_file = os.path.join(DATA_DIR, "users.json")
    
    if os.path.exists(user_file):
        with open(user_file) as f:
            users = json.load(f)
            
        return users
    else:
        return []

@st.cache(allow_output_mutation=True)
def get_spreadsheet_client():
    sheet = Spreadsheet(spreadsheet_id=SPREADSHEET_ID)
    sheet.connect()
    
    return sheet

@st.cache
def load_tasks():
    return pd.read_csv(os.path.join(DATA_DIR, "summaries.csv.zip"))

@st.cache(hash_funcs={redis.Redis: id})
def get_redis_connection():
    return redis.Redis(host=os.getenv("REDIS_SERVER", "localhost"), port=6379, password=os.getenv("REDIS_PASSWORD"))

@st.cache(allow_output_mutation=True)
def get_user_work(username):
        
    data_file = os.path.join(DATA_DIR, f"user_{username}.jsonl")
    work = []
    
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            for line in f:
                work.append(json.loads(line))
    return work


@st.cache(allow_output_mutation=True)
def get_all_completed():
    """Get hashes for all tasks completed by all users"""
    all_work = []
    
    for user in get_users():
        work = get_user_work(user['name'])
        for task in work:
            all_work.append((task['hash'], task.get('iaa',False)))

    return all_work

def get_iaa_tasks():
    return set([hash for hash, is_iaa in get_all_completed() if is_iaa])

def get_completed_hashset():
    return set([hash for hash, _ in get_all_completed()])

@st.cache(allow_output_mutation=True)
def get_interesting_tasks():
    """Get all interesting/difficult tasks from google sheets"""
    all_complete = dict()
    sheet = get_spreadsheet_client()
    for (hash, user, comment) in sheet.get_range(INTERESTING_RANGE)['values']:
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
        
        elif user_password != SECRET:
            st.header("Log in")
            st.write("please provide the password now")
        
        else:
            
            self.user = self.get_user_profile(user_selector)
            self.task_df = load_tasks()
            self.info_ph = st.sidebar.empty()
            
            self.nav_header_ph = st.sidebar.empty()
            self.task_id_ph = st.sidebar.empty()
            self.task_decide_ph = st.sidebar.empty()
            
            self.task_question_ph = st.empty()


            
            st.markdown("Use the below buttons to add this task to the interesting or frame sheets. You need to do this before you give a Yes/No/Report answer")
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
            
            self.show_task(user_selector) 
            
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
        get_frame_tasks()[task['hash']] = self.user['name']

    def add_interesting_task(self, task):
        self.add_sheet_task(task, INTERESTING_RANGE)
        #append to cache
        get_interesting_tasks()[task['hash']] = self.user['name']
        
    def add_sheet_task(self, task, range):
        # generate text
        entity = task['News Candidates'].split(";")[0]
        sci_entity = task['Abstract Candidates'].split(";")[0]
        comment = f"{entity} and {sci_entity}"
        
        #append to actual sheet
        sheet = get_spreadsheet_client()
        row = [task['hash'], self.user['name'], comment]
        sheet.append_sheet(range, [row])
        

        
        
        


            
    def handle_task_outcome(self):
        if self.yes_btn or self.no_btn or self.report_btn:
            
            if self.redis.get(f"user_{self.user['name']}_task_id") is not None:
                self.last_task_id =  self.redis.get(f"user_{self.user['name']}_task_id").decode("utf8")
            
            if self.last_task_id is None:
                st.error("You clicked OK but I couldn't find the task in redis...")
                return
            
            prevtask = self.task_df.loc[self.task_df.hash == self.last_task_id].to_dict(orient='records')[0]
            
            # there is a random chance that this will become an IAA task
            if np.random.random() < float(os.getenv('IAA_RATIO', 0.3)):
                prevtask['iaa'] = True
            
            if self.yes_btn:
                prevtask['label'] = 'yes'
            elif self.no_btn:
                prevtask['label'] = 'no'
            elif self.report_btn:
                prevtask['label'] = 'invalid'

            #write exercise to cache
            work = get_user_work(self.user['name'])
            work.append(prevtask)
            
            all_work = get_all_completed()
            all_work.append((prevtask['hash'], prevtask.get('iaa', False)))
            
            # store exercise 'properly' in file
            self.append_user_work(self.user['name'], prevtask)
            

            
    def update_progress(self, done):
        self.info_ph.markdown("You have done {} tasks! Hooray!".format(done))
            
    def manage_task_navigation(self, todo):
        
        self.nav_header_ph.header("Task Navigation")
        
        task_decide = self.task_decide_ph.radio('Current task', ['random', 'from task ID'])

        next_task = None
        
        if task_decide =='random':
            
            next_task = todo.iloc[0] # next one should be next most similar
            task_id = self.task_id_ph.text_input('Task Id (Magic ID you can use to find this task again)', value=next_task['hash'])
            
        elif task_decide == 'from task ID':
            
            task_id = self.task_id_ph.text_input('Task Id (Magic ID you can use to find this task again)', value='')
            if task_id != '':
                next_task = self.task_df.loc[self.task_df.hash == task_id].iloc[0]
            else:
                st.markdown("# Please enter a task ID to navigate to it\n\n A task ID is a SHA hash like `bf4f745552980203a2a2b6e641b0c069141c7f8e2f9f81466fa112c59e9a1274`")
        
        self.last_task_id =  self.redis.set(f"user_{self.user['name']}_task_id", task_id)
        
        return next_task
        

    def show_task(self, username):
        
        work = get_user_work(username)
        
        user_done_hashes = set([task['hash'] for task in work])
        iaa_tasks = get_iaa_tasks()
        
        not_done_iaa = iaa_tasks - user_done_hashes
        
        
        #prioritise iaa tasks
        if len(self.task_df[self.task_df.hash.isin(not_done_iaa)]) > 0:
            todo = self.task_df[self.task_df.hash.isin(not_done_iaa)]
        else:
            all_done = get_completed_hashset()
            todo = self.task_df[~self.task_df.hash.isin(all_done)]
            #todo = self.task_df[~self.task_df.hash.isin(user_done_hashes)]
        
        self.update_progress(len(user_done_hashes))
        
        next_task = self.manage_task_navigation(todo)
        
        if next_task is not None:
            
            self.show_task_spreadsheet_options(next_task)
            self.handle_sheet_updates(next_task)

            try:
                entity, start, end = next_task['News Candidates'].split(";")
                
                buffer = next_task['Summary'][:int(start)].strip() + " **" + entity + "** " + next_task['Summary'][int(end):].strip()
                
                sci_entity, start, end = next_task['Abstract Candidates'].split(";")
                
                next_task['abstract'] = next_task['abstract'].replace("\s+"," ")
                
                sci_buffer = next_task['abstract'][:int(start)].strip() + " **" + sci_entity + "** " + next_task['abstract'][int(end):].strip()
                
                self.task_question_ph.markdown(f"## Are *'{entity}'* and *'{sci_entity}'* mentions of the same thing?")
                

            except ValueError:
                
                st.markdown("There was a problem with this task. Click Report to continue.")
            
            #skip = st.button("Skip (you will see this again)")
            sci_buffer = re.sub("^\s+","\n", sci_buffer, flags=re.MULTILINE)
            
            self.task_markdown_ph.markdown(f"## News Summary [[link]]({next_task['URL']})\n" 
                        + buffer 
                        + f"\n\n\n## Science Abstract [[link]](https://dx.doi.org/{next_task['doi']})\n" 
                        + sci_buffer.strip())
            
            
    
    def show_task_spreadsheet_options(self, task):
        
        if task['hash'] not in get_interesting_tasks():
            self.interesting_btn = self.interesting_btn_ph.button("Interesting Task (Append Spreadsheet)")
        else:
            self.interesting_btn_ph.markdown(f"**Task already in interesting list, added by {get_interesting_tasks()[task['hash']]}**")
            
        if task['hash'] not in get_frame_tasks():
            self.frame_btn = self.frame_btn_ph.button("Interesting Frame (Append Spreadsheet)")
        else:
            self.frame_btn_ph.markdown(f"**Task already exists in frame list, added by {get_frame_tasks()[task['hash']]}**")


    def user_list(self):
        
        options = ["---"] + [user['name'] for user in get_users()]
                
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
            
    def get_user_profile(self, username):
        users = get_users()
        for user in users:
            if user['name'] == username:
                return user
        else:
            return None
        

    def show_front_page(self):
        
        with open(os.path.join(ASSETS_DIR, "README.md")) as f:
            st.markdown(body=f.read())
            
        st.markdown("**If you are a returning user, select your username in the sidebar. If you are new create your profile below.**")
        
        username = st.text_input("Enter a username:")
        
        cb = st.button("Create a user profile")
        
        if cb:
            self.add_user(username)
            st.write("Thank you for creating a new user... Please refresh your browser to log in.")
        

    def append_user_work(self, username, work):
        data_file = os.path.join(DATA_DIR, f"user_{username}.jsonl")
        
        with open(data_file, "a") as f:
            f.write(json.dumps(work) + "\n")

    def taskhash(self, row):
        h = hashlib.new("sha256", row['URL'] + row['DOI'] + row['News Candidates'] + row['Abstract Candidates'])
        return h.hexdigest()




            
            


            
app = CDCRTool()
app.init_ui()

