import os
import flask
import hashlib

from flask_security import SQLAlchemySessionUserDatastore, Security
from flask_cors import CORS
from flask_restful import Api
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine(os.getenv("SQLALCHEMY_DB_URI"), convert_unicode=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                        autoflush=False,
                                        bind=engine))

def gravatar_for_email(email):
    m = hashlib.md5()
    m.update(email.encode("utf8"))

    return "https://www.gravatar.com/avatar/{}".format(m.hexdigest())


def create_app():

    app = flask.Flask(import_name="cdcrapp", 
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
    template_folder=os.path.join(os.path.dirname(__file__), "templates"))

    api = Api(app, prefix='/api/v1')

    CORS(app)
    
    # configure app
    app.config.from_object("cdcrapp.settings")


    from cdcrapp.model import Base, User, Role
    from cdcrapp.services import UserService, TaskService
    Base.query = db_session.query_property()
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()


    # Setup Flask-Security
    user_datastore =  SQLAlchemySessionUserDatastore(db_session, User, Role)
    security = Security(app, user_datastore)

    #from .views import bp
    from .resources import TaskResource, AnswerResource, UserResource

    api.add_resource(UserResource, "/user")
    api.add_resource(TaskResource, "/task", "/task/<task_hash>")
    api.add_resource(AnswerResource, "/task/<int:task_id>/answers")



    from flaskext.markdown import Markdown

    Markdown(app)


    # register routes
    #app.register_blueprint(bp)

    #register gravatar function
    app.jinja_env.globals['gravatar_for_email'] = gravatar_for_email

    return app