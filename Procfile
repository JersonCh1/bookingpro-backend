web: python manage.py collectstatic --noinput --clear && gunicorn bookings_saas.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
