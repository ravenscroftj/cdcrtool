from datetime import datetime

from flask import current_app
from flask_restful import Resource, fields, marshal, reqparse
from flask_security import auth_required, current_user

from cdcrapp.services import FlaskTaskService
from cdcrapp.model import Task, UserTask
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
        "is_bad_user_id": fields.Integer,
        "is_bad_reported_at": fields.DateTime,
        "sci_paper_id": fields.Integer,
        "news_url": fields.String,
        "news_text": fields.String,
        "sci_url":fields.String,
        "sci_text":fields.String
    }

    @auth_required('token')
    def get(self):

        parser = reqparse.RequestParser()
        parser.add_argument('hash', type=str, required=False)

        args = parser.parse_args()

        if args.hash is not None:
            t = db_session.query(Task).filter(Task.hash==args.hash).one_or_none()

            if not t:
                return {"error":f"No task exists with hash={args.hash}"}, 404
        else:

            # get user's current next task
            tasksvc = FlaskTaskService(engine=None)

            t = tasksvc.next_tasks_for_user(current_user)


        return marshal(t, self.task_fields)

    @auth_required('token')
    def post(self):
        """Give user the opportunity to report a task as 'bad'"""

        parser = reqparse.RequestParser()
        parser.add_argument('task_id', type=str, required=True)
        parser.add_argument('is_bad', type=bool, required=False, default=False)
        parser.add_argument('is_bad_reason', type=str, required=False)

        args = parser.parse_args()

        t = db_session.query(Task).filter(Task.id==args.task_id).one_or_none()

        if not t:
            return {"error":f"No such task with id={args.task_id}"}, 404
        else:
            t.is_bad = args.is_bad
            if args.is_bad:
                t.is_bad_reason = args.is_bad_reason
                t.is_bad_user_id = current_user.id
                t.is_bad_reported_at = datetime.now()
            else:
                t.is_bad_reason = None
                t.is_bad_user_id = None
                t.is_bad_reported_at = None
            
        db_session.add(t)
        db_session.commit()

        return marshal(t, self.task_fields)



class AnswerResource(Resource):

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
    def post(self, task_id):
        parser = reqparse.RequestParser()
        parser.add_argument('answer', type=str, required=True, choices=['yes','no'])
        args = parser.parse_args()

        ut = UserTask(task_id=task_id, user_id=current_user.id, answer=args.answer)

        db_session.add(ut)
        db_session.commit()

        return marshal(ut, self.ut_fields), 201


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