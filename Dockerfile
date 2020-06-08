FROM tiangolo/meinheld-gunicorn-flask:python3.6


COPY ./requirements.txt /app/
RUN pip install -r requirements.txt


COPY ./cdcrapp /app/cdcrapp
COPY ./client/build /app/client/build



ENV PYTHONPATH=$PYTHONPATH:/app/
ENV MODULE_NAME="cdcrapp.web.wsgi"