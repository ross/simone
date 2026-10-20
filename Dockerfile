FROM python:3.15-slim

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN python -m nltk.downloader punkt_tab
COPY . .
RUN find /app

CMD script/run
