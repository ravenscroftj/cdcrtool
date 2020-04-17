# CDCR ground truthing app

This application can be used to generate ground truth data for the purpose of cross docment coreference resolution.

## Installing


### Python

You need Python 3.6 and [poetry](https://python-poetry.org/). Simply run:

`poetry install` 

to install required python modules

### Supporting services

This tool uses a Postgres database (since we use sqlalchemy you could use any suitable db in the backend including sqlite)

We also use redis to temporarily hold state in between page loads.

The package comes with a `docker-compose.yml` which you can use to set up redis, Postgres and Adminer (a web ui for Postgres administration). If you have docker and docker compose installed, simply run: `docker compose up -d` to enable these services.


## Configuring

You will need a .env file with settings for connecting to the database. Use `env.example` as a guide and rename to `.env` so that the app picks up your settings on execution. You can also use environment variables instead if you wish.

### Set up database 

Before you run the application you need to generate the database tables. You can do this by running:

`poetry run alembic upgrade head`

## Running

To run the tool run `poetry run streamlit run --server.runOnSave true cdcrapp/stapp.py` from the commandline.