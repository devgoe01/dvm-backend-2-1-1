#!/bin/sh
python manage.py makemigrations
#python manage.py collectstatic --no-input
python manage.py migrate
exec "$@"