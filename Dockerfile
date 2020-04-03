from python:3.5

COPY . .
RUN pip install -r requirements.txt
ENV PYTHONPATH .
WORKDIR .
