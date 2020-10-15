# CDCR ground truthing app

This application can be used to generate ground truth data for the purpose of cross docment coreference resolution.


## Dataset Access

Due to copyright restrictions we are currently unable to offer the CD$^2$CR corpus as a direct download. However we have provided a script that can be run for free in Google Colab that will generate the corpus for you for your own personal or academic use. The script takes ~20 minutes and provides a standard CONLL formatted corpus at the end.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/11ARcCOsCFBTOG9vw64sAfashjDQzv7Ci?usp=sharing)


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

## Exporting data

Exporting the data is a 2 phase process. Firstly you must generate JSON dump. Secondly you can create CONLL-compatible files.


### Export JSON
First to export json you can run

`poetry run python -m cdcrapp export-json dump.json --seed=42 --split=0.7`

The script will generate test and train files and entity maps so the above command will generate 4 files:

```
dump_train.json
dump_train_entities.json
dump_test.json
dump_test_entities.json
```

Split allows us to specify the ratio of the train and test sets so in this case train will be 70% of data and train 30%.

Seed is the random seed used for shuffling the data. this may be useful if you wish to re-create the same shuffle many times. Seed defaults to `42` which might be confusing if you are expecting different random behaviour but you don't set the seed.

### Export CONLL

The next step is to export CONLL data. This is done with the following command:

`poetry run python -m cdcrapp export-conll dump_test.json ./test.conll`

The command should be run for both `dump_test.json` and `dump_train.json` separately and it will automatically find the associated entities files.