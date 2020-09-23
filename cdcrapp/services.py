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
from sqlalchemy.orm import joinedload

from cdcrapp.kappa import fleiss_kappa

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

    def list(self, objtype: ModelBase, filters={}, limit:int=None, joins=[], offset:int=None, orderby=None) -> List[ModelBase]:
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

            for join in joins:
                q = q.join(join)
        
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

    def get_fleiss_iaa(self, just_difficult=False) -> float:

        with self.session() as session:
            q = session.query(UserTask)\
                .join(User)\
                .join(UserTask.task)

            if just_difficult:
                q = q.filter(UserTask.task_id.in_(session.query(Task.id).filter(Task.is_difficult)))

            all_data = defaultdict(lambda: list())

            print(q)

            for ut in q.all():
                all_data[ut.task_id].append((ut.user.username, ut.answer))

        grouped_tasks = defaultdict(lambda:set())

        print(len(all_data))
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
                .join(UserTask.user)\
                .join(UserTask.task)\
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
        

    def get_by_hash(self, hash:str, allow_wildcard: Optional[bool]=False) -> Optional[Task]:
        """Get task by hash"""

        with self.session() as session:
            if allow_wildcard:
                q = session.query(Task).filter(Task.hash.ilike(f"{hash}%"))
            else:
                q = session.query(Task).filter(Task.hash==hash)
            
            return q.one_or_none()

    def remove_tasks_by_doc_ids(self, news_article_id, sci_paper_id):
        """Bulk remove tasks that tie together a particular pair of documents (erroneously)"""

        with self.session() as session:

            # remove user tasks associated with tasks being deleted
            session.query(UserTask).filter(UserTask.task_id.in_(session.query(Task.id)
                .filter_by(news_article_id=news_article_id, sci_paper_id=sci_paper_id))
                ).delete(synchronize_session='fetch')

            return session.query(Task).filter_by(news_article_id=news_article_id, sci_paper_id=sci_paper_id).delete()
    
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
                    Task.priority.desc(),
                    Task.is_iaa_priority.desc(), 
                    Task.similarity.desc()
                    )).first()

    def get_task_doc_coverage(self, min_coverage=0):
        """Get document coverage for tasks"""

        from sqlalchemy import text

        with self.session() as session:

            conn = session.connection()

            conn.execute("""DROP TABLE IF EXISTS news_complete""")
            conn.execute("""DROP TABLE IF EXISTS news_total""")

            conn.execute("""CREATE TEMP TABLE news_complete AS 
            SELECT newsarticles.id as news_id, count(newsarticles.id) as completed_tasks 
            FROM newsarticles LEFT JOIN tasks ON newsarticles.id=tasks.news_article_id  
            WHERE tasks.id in (SELECT DISTINCT user_tasks.task_id from user_tasks)
            GROUP BY newsarticles.id;""")

            conn.execute("""CREATE TEMP TABLE news_total AS 
            SELECT newsarticles.id as news_id, count(newsarticles.id) as total_tasks FROM newsarticles 
            LEFT JOIN tasks ON newsarticles.id=tasks.news_article_id 
            WHERE (tasks.is_bad is null or tasks.is_bad = false)
            GROUP BY newsarticles.id;""")

            result = conn.execute(text("""SELECT news_complete.news_id, 
                                       news_total.total_tasks, 
                                       news_complete.completed_tasks, 
                                       (SELECT news_complete.completed_tasks * 100 / news_total.total_tasks ) as complete_percent 
                        FROM news_complete LEFT JOIN news_total ON news_complete.news_id=news_total.news_id
                        ORDER BY complete_percent DESC;"""), min=min_coverage)

            columns = ['news_id','news_total','news_complete','complete_percent']
            for r in result.fetchall():
                row = {key:value for value,key in zip(r,columns)}
                if row['complete_percent'] >= min_coverage:
                    yield row
        
    def get_annotated_tasks(self, limit:Optional[int]=None, offset:Optional[int]=None, exclude_users=[], min_coverage=None) -> List[Task]:
        """Select tasks that have been annotate by at least 1 user"""

        with self.session() as session:

            # find document coverage


            ut_task_ids = session.query(UserTask.task_id).distinct().filter(~UserTask.user_id.in_(exclude_users))
            q = session.query(Task).filter(Task.id.in_(ut_task_ids)).join(NewsArticle).join(SciPaper).join(UserTask)


            if min_coverage is not None:
                covered_ids = [c['news_id'] for c in self.get_task_doc_coverage(min_coverage=min_coverage)] 
                q = q.filter(Task.news_article_id.in_(covered_ids))

            if limit is not None:
                q = q.limit(limit)

            if offset is not None:
                q = q.offset(offset)


            return q.options(joinedload('usertasks')).all()

    def get_answer_dists(self)  -> List[tuple]:
        with self.session() as session:
            q = session.query(UserTask.answer, func.count(UserTask.task_id.distinct())).join(Task).filter(~Task.is_bad).group_by(UserTask.answer)
            return(q.all())
            
    def get_task_difficulty_dist(self, answered=True, only_difficult=False) -> np.ndarray:
        """Return a distribution of difficulties"""

        with self.session() as session:
            

            q = session.query(Task).filter(~Task.is_bad, Task.similarity != None)
            
            if only_difficult:
                q = q.filter(Task.is_difficult==True)
                
            if answered:
                subq = session.query(UserTask.task_id.distinct())
                q = q.filter(Task.id.in_(subq))

            return np.array([t.similarity for t in q.all()])

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

class FlaskUserService(UserService):

    @contextmanager
    def session(self):
        from cdcrapp.web import db_session
        yield db_session

class FlaskTaskService(TaskService):
    @contextmanager
    def session(self):
        from cdcrapp.web import db_session
        yield db_session