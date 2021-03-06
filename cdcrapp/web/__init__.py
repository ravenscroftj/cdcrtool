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

    client_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../client/build"))

    app = flask.Flask(import_name="cdcrapp", 
    static_folder=client_path)

    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):

        print(path)

        if path != "" and os.path.exists(os.path.join(flask.current_app.static_folder, path)):
            return flask.current_app.send_static_file(path)
        else:
            return flask.current_app.send_static_file("index.html")


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
    from .resources import TaskResource, AnswerListResource, UserResource, EntityResource\
        , UserTaskListResource, BatchAnswerResource, SingletonAnswerResource


    api.add_resource(UserResource, "/user")
    api.add_resource(TaskResource, "/task", "/task/<task_hash>")
    api.add_resource(BatchAnswerResource, "/answers")
    api.add_resource(SingletonAnswerResource, "/task/singletons")
    api.add_resource(AnswerListResource, "/task/<int:task_id>/answers")
    api.add_resource(EntityResource, "/entities/<string:doc_type>/<int:doc_id>")
    api.add_resource(UserTaskListResource, "/user/tasks")



    from flaskext.markdown import Markdown

    Markdown(app)


    # register routes
    #app.register_blueprint(bp)

    #register gravatar function
    app.jinja_env.globals['gravatar_for_email'] = gravatar_for_email

    return app