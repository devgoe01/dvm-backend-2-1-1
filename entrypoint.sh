#!/bin/sh
python manage.py makemigrations
#python manage.py collectstatic --no-input
python manage.py migrate
gunicorn bus_service.wsgi:application --bind 0.0.0.0:1337 --workers 3 --threads 2 --timeout 120 