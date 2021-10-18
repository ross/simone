FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
RUN find /app

# TODO: migrate first, run in gunicorn
CMD ./manage.py runserver 0.0.0.0:6444
