#!/usr/bin/env python
import os
import sys


def main():
    # Dev por defecto; en Railway se sobreescribe con DJANGO_SETTINGS_MODULE=bookings_saas.settings.prod
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookings_saas.settings.dev')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Activaste el virtualenv?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
