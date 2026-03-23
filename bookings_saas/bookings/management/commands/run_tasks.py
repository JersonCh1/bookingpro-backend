"""
Comando para ejecutar tareas periódicas manualmente.
Usar en Railway scheduler o cron externo.

Uso:
  python manage.py run_tasks reminder   → recordatorios 24h
  python manage.py run_tasks ratings    → solicitudes de valoración
  python manage.py run_tasks summary    → resumen diario al negocio
  python manage.py run_tasks all        → todas las tareas
"""
from django.core.management.base import BaseCommand
from bookings_saas.bookings.tasks import (
    send_reminder_24h,
    send_rating_requests,
    send_daily_summary,
)


class Command(BaseCommand):
    help = 'Ejecuta tareas periódicas de notificación'

    def add_arguments(self, parser):
        parser.add_argument(
            'task',
            nargs='?',
            default='all',
            choices=['reminder', 'ratings', 'summary', 'all'],
            help='Tarea a ejecutar (default: all)',
        )

    def handle(self, *args, **options):
        task = options['task']

        if task in ('reminder', 'all'):
            self.stdout.write('→ Enviando recordatorios 24h...')
            n = send_reminder_24h()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {n} recordatorios enviados'))

        if task in ('ratings', 'all'):
            self.stdout.write('→ Enviando solicitudes de valoración...')
            n = send_rating_requests()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {n} solicitudes enviadas'))

        if task in ('summary', 'all'):
            self.stdout.write('→ Enviando resúmenes diarios...')
            n = send_daily_summary()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {n} resúmenes enviados'))
