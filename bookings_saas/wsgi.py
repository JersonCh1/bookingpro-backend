import os
from django.core.wsgi import get_wsgi_application

# Railway sobreescribe esta variable via DJANGO_SETTINGS_MODULE=bookings_saas.settings.prod
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookings_saas.settings.dev')

application = get_wsgi_application()
