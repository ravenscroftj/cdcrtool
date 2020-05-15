import random
import numpy as np
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional, ContextManager
from cdcrapp.model import User, Task, UserTask, NewsArticle, SciPaper, Base as ModelBase

from collections import defaultdict, Counter

from sklearn.metrics import cohen_kappa_score
from itertools import combinations

from crypt import crypt, mksalt, METHOD_SHA512
from contextlib import contextmanager
from sqlalchemy import func

from kappa import fleiss_kappa

class DBServiceBase(object):
    engine: Engine
    Session: sessionmaker
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.session_factory = sessionmaker(bind=self.engine)   
        
    @contextmanager
    def session(self) -> Session:

        with self.engine.begin() as conn:
            session: Session = self.session_factory(bind=conn)
            yield session
            session.close()
    
    @contextmanager
    def update(self, obj: ModelBase) -> ModelBase:
        """Commit changes to a database object"""
        with self.session() as session:
            session.add(obj)
            session.commit()
        
    def list(self, objtype: ModelBase, filters={}, limit:int=None, offset:int=None, orderby=None) -> List[ModelBase]:
        """List all items of given type"""

        with self.session() as session:
            q = session.query(objtype)
            if limit is not None:
                q = q.limit(limit)
                
            if offset is not None:
                q = q.offset(limit)
        
            if orderby != None:
                q = q.order_by(**orderby)

            if len(filters) > 0:
                if isinstance(filters, dict):
                    q = q.filter_by(**filters)
                elif isinstance(filters, list):
                    q = q.filter(*filters)
        
            return q.all()


        
    def get_by_filter(self, objtype, **kwargs):
        """Get a database record by type using filters"""
        
        with self.session() as session:
            return session.query(objtype).filter_by(**kwargs).one_or_none()

class UserService(DBServiceBase):


    def update_password(self, user: User, password: str) -> User:

        salt = mksalt(METHOD_SHA512)

        user.password = crypt(password, salt)
        user.salt = salt
        
        with self.session() as session:
            session.add(user)
            session.commit()
            return user
    
    def add_user(self, username, password, email) -> User:
        
        salt = mksalt(METHOD_SHA512)
        
        u = User(username=username, password=crypt(password, salt), email=email, salt=salt)
        
        with self.session() as session:
            session.add(u)
            session.commit()
            return u
        
    def authenticate(self, username, password) -> bool:
        u = self.get_by_username(username)
        if not u:
            return False
        else:
            return crypt(password, u.salt) == u.password
        
    def get_by_username(self, username) -> Optional[User]:
        
        return self.get_by_filter(User, username=username)
    
    def get_progress_for_user(self, user: User) -> int:
        with self.session() as session:
            session.add(user)
            return session.query(UserTask).filter(UserTask.user_id==user.id).count()
    
    def user_add_task(self, user: User, task: Task, answer: str) -> UserTask:
        from sqlalchemy import func
        with self.session() as session:
            ut = UserTask(task=task, user=user, answer=answer)
            session.add(ut)
            session.commit()
    
    
    def get_all_user_progress(self) -> List[tuple]:
        
        # session: Session 
        with self.session() as session:
            result = session.query(User.username, func.count(User.username)).join(UserTask).group_by(User.username).all()
            
        return result

    def get_user_statistics(self):
        """List basic annotation stats for each user"""

        with self.session() as session:

            q = session.query(User.username, UserTask.answer, func.count(UserTask.user_id))\
                .filter(User.id==UserTask.user_id)\
                    .group_by(User.username, UserTask.answer)

            user_answers = defaultdict(lambda:{})
            for username, answer, count in q.all():
                user_answers[username][answer] = count

            for user in user_answers:
                row = [user]
                total = sum(user_answers[user].values())
                
                for answer in ['yes','no']:
                    n = user_answers[user].get(answer,0)
                    row.append(f"{round(n/total * 100, 2)} % ({n})")

                yield row

    def get_fleiss_iaa(self) -> float:

        with self.session() as session:
            q = session.query(UserTask)\
                .join(User)\
                .join(Task)

            all_data = defaultdict(lambda: list())

            for ut in q.all():
                all_data[ut.task_id].append((ut.user.username, ut.answer))

        grouped_tasks = defaultdict(lambda:set())

        for task_id, answers in all_data.items():
            biggest_group = tuple(sorted([username for (username,answer) in answers]))

            grouped_tasks[biggest_group].add(task_id)

            if len(biggest_group) > 3:
                for subgroup in combinations(biggest_group, 3):
                    grouped_tasks[subgroup].add(task_id)
            
            if len(biggest_group) > 2:
                for subgroup in combinations(biggest_group, 2):
                    grouped_tasks[subgroup].add(task_id)

        # tidy up subgroups that are the same as the biggest group
        removelist=set()
        for i, (group, values) in enumerate(sorted(grouped_tasks.items(), key=lambda x:len(x[1]), reverse=True)):
            for g2, vals2 in sorted(grouped_tasks.items(), key=lambda x:len(x[1]), reverse=True)[i+1:]:

                if values == vals2:
                    removelist.add(g2)

        for group in removelist:
            del grouped_tasks[group]

        for group, tasks in sorted(grouped_tasks.items(), key=lambda x:len(x[0]), reverse=True):

            if len(group) < 2:
                continue

            # generate matrix for answers
            ratings = []

            for t_id in tasks:
                ratings.extend([(t_id, ans) for user,ans in all_data[t_id] if user in group])


            #print(ratings)
            k = fleiss_kappa(ratings, n=len(group), k=2)

            yield (",".join(group), len(tasks), k)


        #breakdown = {group:len(tasks) for group,tasks in grouped_tasks.items()}


        #print(f"Found {len(all_data)}")


        #print(f"Breakdown: {breakdown}")
            
    
    def get_pairwise_iaa(self, usernameA: str, usernameB: str) -> float:
        
        with self.session() as session:
            q = session.query(UserTask)\
                .join(User)\
                .join(Task)\
                .filter(
                    (User.username==usernameA) | (User.username==usernameB),
                    Task.is_iaa == True
                )
            
            results = q.all()
            
            userA_answers = []
            userB_answers = []
            
            for r in results:
                if r.user.username == usernameA:
                    userA_answers.append(r)
                elif r.user.username == usernameB:
                    userB_answers.append(r)
            
            intersection = set([ut.task_id for ut in userA_answers]).intersection([ut.task_id for ut in userB_answers])
            
            # sort answers by task id ascending
            userA_answers = sorted(userA_answers, key=lambda x: x.task_id)
            userB_answers = sorted(userB_answers,  key=lambda x: x.task_id)
            
            y_a = [ut.answer for ut in userA_answers if ut.task_id in intersection]
            y_b = [ut.answer for ut in userB_answers if ut.task_id in intersection]
        
        return cohen_kappa_score(y_a, y_b)
                    
                
 

class TaskService(DBServiceBase):
    
    def add_tasks(self, tasks: List[Task]):
        """Bulk import tasks from external source"""
        
        with self.session() as session:
            session.add_all(tasks)
            session.commit()
        

    def get_by_hash(self, hash) -> Optional[Task]:
        """Get task by hash"""
        return self.get_by_filter(Task, hash=hash)
    
    def next_tasks_for_user(self, user: User) -> Task:
        """List tasks that a given user has not yet completed"""
        
        with self.session() as session:
            session.add(user)

            # list of user tasks that the current user has completed
            substmt = session.query(UserTask.task_id).filter(UserTask.user_id == user.id)

            # list of task ids completed by other users excluding those in the current IAA priority list
            completed = session.query(Task.id).join(UserTask).filter(~Task.is_iaa_priority)

            return (session.query(Task).filter(
                ~Task.id.in_(substmt), 
                ~Task.id.in_(completed),
                ~Task.is_bad)
                .order_by(
                    Task.is_iaa_priority.desc(), 
                    Task.similarity.desc()
                    )).first()
        
    def rebalance_iaa(self, max_priority_tasks: int = 150):
        """Rebalance IAA tasks"""

        with self.session() as session:

            iaa_tasks = session.query(Task).filter(Task.is_iaa).all()
            priority_tasks = session.query(Task).filter(Task.is_iaa_priority).all()

            for task in priority_tasks:
                task.is_iaa_priority = False

            session.bulk_save_objects(priority_tasks)

            new_pri_tasks = random.sample(iaa_tasks, max_priority_tasks)

            for task in new_pri_tasks:
                task.is_iaa_priority = True
            
            session.bulk_save_objects(new_pri_tasks)

            session.commit()
