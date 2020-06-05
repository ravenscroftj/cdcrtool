from flask import Blueprint, render_template, current_app, request, redirect, url_for
from flask_security import login_required
#from ranky.models import db, Article, ArticleSentence, UserAnnotation
from flask_security.core import current_user

bp = Blueprint("main", import_name=__name__)

@bp.route("/", methods=['GET'])
@login_required
def index():
    return render_template("main.html", current_user=current_user)
