#!/bin/sh
if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for PostgreSQL..."

    while ! nc -z $SQL_HOST $SQL_PORT; do sleep 0.1; done

    echo "PostgreSQL started"
fi

#python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate --no-input
#gunicorn bus_service.wsgi:application --bind 0.0.0.0:8000 --workers 3 --threads 2 --timeout 120 

exec "$@"