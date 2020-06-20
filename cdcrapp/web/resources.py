import os
import numpy as np

from datetime import datetime

from collections import defaultdict
from sqlalchemy import update

from flask import current_app
from flask_restful import Resource, fields, marshal, reqparse
from flask_security import auth_required, current_user

from cdcrapp.services import FlaskTaskService
from cdcrapp.model import Task, UserTask, NewsArticle, SciPaper
from cdcrapp.web import db_session

        


class TaskResource(Resource):

    task_fields = {
        "id": fields.Integer,
        "hash": fields.String,
        "news_ent": fields.String,
        "sci_ent": fields.String,
        "similarity": fields.Float,
        "is_iaa": fields.Boolean,
        "is_iaa_priority": fields.Boolean,
        "is_bad": fields.Boolean,
        "is_bad_reason": fields.String,
        "is_difficult": fields.Boolean,
        "is_difficult_user": fields.String(attribute="is_difficult_user.username"),
        "is_difficult_reported_at": fields.DateTime,
        "is_bad_user_id": fields.Integer,
        "is_bad_reported_at": fields.DateTime,
        "news_article_id": fields.Integer,
        "sci_paper_id": fields.Integer,
        "news_url": fields.String,
        "news_text": fields.String,
        "sci_url":fields.String,
        "sci_text":fields.String,
        "priority": fields.Integer
    }

    @auth_required('token')
    def get(self):

        parser = reqparse.RequestParser()
        parser.add_argument('hash', type=str, required=False)
        parser.add_argument('news_id', type=int, required=False)
        parser.add_argument('science_id', type=int, required=False)
        parser.add_argument('news_ent',type=str,required=False)
        parser.add_argument('sci_ent',type=str,required=False)

        args = parser.parse_args()

        if args.hash is not None:
            t = db_session.query(Task).filter(Task.hash==args.hash).one_or_none()

            if not t:
                return {"error":f"No task exists with hash={args.hash}"}, 404

        elif args.news_id is not None or args.science_id is not None or args.news_ent is not None or args.sci_ent is not None:

            # we need all 4 to be able to continue
            errors = []

            if args.news_id is None:
                errors.append("You must set news_id")
            if args.science_id is None:
                errors.append("You must set science_id")
            if args.news_ent is None:
                errors.append("You must set news_ent")
            if args.sci_ent is None:
                errors.append("You must set sci_ent")

            if len(errors) > 0:
                errorstring = ";".join(errors)
                return {"error":f"In order to use this endpoint to find specific tasks by entity, {errorstring}"}, 400


            print(args)
            t = db_session.query(Task).filter(Task.news_article_id==args.news_id, 
                Task.sci_paper_id==args.science_id, 
                Task.news_ent==args.news_ent, 
                Task.sci_ent==args.sci_ent).one_or_none()

            if not t:
                return {"error":"cannot find a task with that combination of entities and articles."},404


        else:

            # get user's current next task
            tasksvc = FlaskTaskService(engine=None)

            t = tasksvc.next_tasks_for_user(current_user)

        tfields = dict(**self.task_fields)
        
        tfields.update({ 
            'sci_ents': fields.List(fields.String),
            'news_ents': fields.List(fields.String),
            "related_answers": fields.Raw
        })

        if t.current_user_answer != None and t.current_user_answer.task_id != 0:
            tfields['current_user_answer'] = fields.Nested({
                'task_id': fields.Integer,
                'answer': fields.String,
                'created_at': fields.DateTime
            })
        
        return marshal(t,  tfields)

    @auth_required('token')
    def post(self):
        """Give user the opportunity to report a task as 'bad'"""

        parser = reqparse.RequestParser()
        parser.add_argument('task_id', type=str, required=True)
        parser.add_argument('is_bad', type=bool, required=False, default=None)
        parser.add_argument('is_bad_reason', type=str, required=False)
        parser.add_argument('is_difficult', type=bool, required=False, default=False)

        args = parser.parse_args()

        t = db_session.query(Task).filter(Task.id==args.task_id).one_or_none()

        if not t:
            return {"error":f"No such task with id={args.task_id}"}, 404
        else:
            
            if args.is_bad is not None:
                t.is_bad = args.is_bad
                if args.is_bad:
                    t.is_bad_reason = args.is_bad_reason
                    t.is_bad_user_id = current_user.id
                    t.is_bad_reported_at = datetime.utcnow()

                    if t.is_bad_reason == "bad sci ent":
                        # update all tasks with same sci ent
                        db_session.query(Task)\
                          .filter(Task.sci_ent==t.sci_ent, Task.sci_paper_id==t.sci_paper_id)\
                          .update({"is_bad":True, "is_bad_reason": t.is_bad_reason})

                    elif t.is_bad_reason == "bad news ent":
                        #update all tasks with same news ent
                        db_session.query(Task)\
                          .filter(Task.news_ent==t.news_ent, Task.news_article_id==t.news_article_id)\
                          .update({"is_bad":True, 
                              "is_bad_reason": t.is_bad_reason, 
                              "is_bad_reported_at": t.is_bad_reported_at,
                              "is_bad_user_id": t.is_bad_user_id })
                else:
                    t.is_bad_reason = None
                    t.is_bad_user_id = None
                    t.is_bad_reported_at = None
            
            if args.is_difficult is not None:
                t.is_difficult = args.is_difficult

                if t.is_difficult:
                    t.is_difficult_user_id = current_user.id
                    t.is_difficult_reported_at = datetime.utcnow()
                else:
                    t.is_difficult_user_id = None
                    t.is_difficult_reported_at = None


            
            
        db_session.add(t)
        db_session.commit()

        return marshal(t, self.task_fields)



class AnswerListResource(Resource):

    ut_fields = {
        "task_id": fields.Integer,
        "answer": fields.String,
        "user_id": fields.Integer
    }

    @auth_required('token')
    def get(self, task_id):
        task = db_session.query(Task).filter(Task.id==task_id).join(UserTask).one()

        answers = [marshal(ans, self.ut_fields) for ans in task.usertasks]

        return answers


    @auth_required('token')
    def patch(self, task_id):
        parser = reqparse.RequestParser()
        parser.add_argument('answer', type=str, required=True, choices=['yes','no'])
        args = parser.parse_args()

        ans = UserTask.query.filter(UserTask.task_id==task_id, UserTask.user_id==current_user.id).one_or_none()

        if ans is None:
            return {"error":f"No answer with task={task_id} and user_id={current_user.id} exists"}, 404

        ans.answer = args.answer
        ans.created_at = datetime.utcnow()

        db_session.add(ans)
        db_session.commit()

        return marshal(ans, self.ut_fields), 200

    @auth_required('token')
    def post(self, task_id):
        parser = reqparse.RequestParser()
        parser.add_argument('answer', type=str, required=True, choices=['yes','no'])
        args = parser.parse_args()

        task = Task.query.get(task_id)

        if task is None:
            return {"error": f"No task with ID={task_id} exists"}, 404

        ut = UserTask(task_id=task_id, user_id=current_user.id, answer=args.answer)

        db_session.add(ut)

        # there is a random chance that this will become an IAA task
        if np.random.random() < float(os.getenv('IAA_RATIO', 0.05)) and (not task.is_iaa):
            task.is_iaa = True
            task.is_iaa_priority = True
        
        db_session.commit()

        return marshal(ut, self.ut_fields), 201


class BatchAnswerResource(Resource):
    """Provide an endpoint for updating multiple answers relating to the same news/science doc combo"""

    def post(self):
        ap = reqparse.RequestParser()
        ap.add_argument("news_article_id", type=int, required=True)
        ap.add_argument("sci_paper_id", type=int, required=True)
        ap.add_argument("answers", action='append',type=dict, required=True)

        args = ap.parse_args()

        tasks = db_session.query(Task).filter(
            Task.news_article_id==args.news_article_id, 
            Task.sci_paper_id==args.sci_paper_id).all()


        taskmap = defaultdict(lambda:[])

        for task in tasks:
            taskmap[(task.news_ent, task.sci_ent)].append(task)

        dbanswers = []
        for answer in args.answers:

            tasks = taskmap.get((answer['news_ent'],answer['sci_ent']))
            existing_answer = False

            if len(tasks) < 1:
                print("create new task")
                t = Task(news_article_id=args.news_article_id, 
                sci_paper_id=args.sci_paper_id, 
                news_ent=answer['news_ent'],
                sci_ent=answer['sci_ent'])

                db_session.add(t)
            else:
                for t in tasks:


                    for ut in t.usertasks:
                        if ut.user_id == current_user.id:
                            ut.answer = answer['answer'],
                            existing_answer = True
                            print(f"Update existing answer (news_ent={t.news_ent}, sci_ent={t.sci_ent}, answer={answer['answer']})")
                            dbanswers.append(ut)
            
                    if not existing_answer:
                        print(f"create answer (news_ent={t.news_ent}, sci_ent={t.sci_ent}, answer={answer['answer']})")
                        ut = UserTask(answer=answer['answer'], user_id=current_user.id, task=t, created_at=datetime.utcnow())
                        db_session.add(ut)

                        dbanswers.append(ut)

        db_session.commit()

        return {"answers":[marshal(ut, ut_fields) for ut in dbanswers]}
        




class EntityResource(Resource):

    def get(self, doc_type, doc_id):
        """Get entities for doc type"""

        if doc_type == "news":
            base_query = Task.query.filter(Task.news_article_id==doc_id)

        elif doc_type == "science":
            base_query = Task.query.filter(Task.sci_paper_id==doc_id)
        else:
            return {"error":"Type of document must be 'news' or 'science"}, 404

        tasks = base_query.all()

        if doc_type == "news":
            entities = set([task.news_ent for task in tasks])
        else:
            entities = set([task.sci_ent for task in tasks])
        
        return {"entities":list(entities)}


    def patch(self, doc_type, doc_id):
        """Update entity"""
        parser = reqparse.RequestParser()
        parser.add_argument('oldEntity', type=str, required=True)
        parser.add_argument('newEntity', type=str, required=True)
        args = parser.parse_args()

        base_query = Task.query

        if(doc_type == "news"):
            base_query = base_query.filter(Task.news_article_id==doc_id, Task.news_ent==args.oldEntity)
        elif(doc_type == "science"):
            base_query = base_query.filter(Task.sci_paper_id==doc_id, Task.sci_ent==args.oldEntity)
        else:
            return {"error":"Type of document must be 'news' or 'science"}, 400

        if doc_type == "news":
            affected = base_query.update({Task.news_ent:args.newEntity})
        else:
            affected = base_query.update({Task.sci_ent:args.newEntity})

        db_session.commit()

        return {"updated_rows":affected}
        
ut_fields = {
    'task_id': fields.Integer,
    'answer': fields.String,
    'task': fields.Nested(TaskResource.task_fields),
    'created_at': fields.DateTime
}

class UserTaskListResource(Resource):

    @auth_required('token')
    def get(self):

        ap = reqparse.RequestParser()
        ap.add_argument("offset", required=False, type=int, default=0)
        ap.add_argument("limit", required=False, type=int, default=200)

        args = ap.parse_args()

        user_tasks = UserTask.query.join(Task.usertasks)\
            .filter(UserTask.user==current_user)\
            .order_by(UserTask.created_at.desc())

        total = user_tasks.count()

        uts = [marshal(ut, ut_fields) for ut in user_tasks.offset(args.offset).limit(args.limit).all()]
    

        return {"total":total, "offset":args.offset, "limit": args.limit, "tasks":uts}

class UserResource(Resource):

    user_fields = {
        'id': fields.Integer,
        'email': fields.String,
        'username': fields.String,
        'total_annotations': fields.Integer
    }

    @auth_required('token')
    def get(self):
        return marshal(current_user, self.user_fields)