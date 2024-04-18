FROM python:3.12-slim-bookworm

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT python run.py