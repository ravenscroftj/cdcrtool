from flask import Blueprint, render_template, current_app, request, redirect, url_for
from flask_security import login_required
#from ranky.models import db, Article, ArticleSentence, UserAnnotation
from flask_security.core import current_user

from cdcrapp.services import FlaskTaskService, FlaskUserService

bp = Blueprint("main", import_name=__name__)

@bp.route("/", methods=['GET'])
@login_required
def index():

    # get user's current next task
    usersvc = FlaskUserService(engine=None)
    tasksvc = FlaskTaskService(engine=None)

    t = tasksvc.next_tasks_for_user(current_user)




    return render_template("main.html", current_user=current_user, task=t)
