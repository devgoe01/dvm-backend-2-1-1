'''#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 mysite.wsgi:application
'''
#!/bin/sh
#python manage.py collectstatic --no-input

python manage.py makemigrations
#python manage.py collectstatic --no-input
python manage.py migrate
exec "$@"