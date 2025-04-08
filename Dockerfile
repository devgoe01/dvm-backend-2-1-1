FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONUNBUFFERED 1

WORKDIR /bus_service

RUN apt-get update && apt-get install -y netcat-openbsd gcc postgresql-client && apt-get clean

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

COPY ./entrypoint.sh /entrypoint2.sh
RUN chmod +x /entrypoint2.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint2.sh"]
