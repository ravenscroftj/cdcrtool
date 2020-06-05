import click
import glob
import json
import os
import tqdm 

from flask import Flask
from flask.cli import AppGroup, with_appcontext

from flask_security.utils import hash_password

from cdcrapp.web.wsgi import app
from cdcrapp.web import db_session
from cdcrapp.model import User

users_cli = app.cli.commands['users']

@click.password_option()
@click.option("--email", type=str, prompt='email')
@users_cli.command("change-password")
@with_appcontext
def change_password(email, password):
    """Change a user's password"""

    u = db_session.query(User).filter(User.email==email).one()

    u.password = hash_password(password)

    db_session.add(u)
    db_session.commit()


