from python:3.5-alpine

COPY . .
RUN pip install -r requirements.txt
ENV PYTHONPATH .
WORKDIR .
