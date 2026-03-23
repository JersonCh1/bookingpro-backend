"""
Management command para configurar el propietario del sistema (superusuario).
Uso: python manage.py setup_owner
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Configura el superusuario principal del sistema con los datos del propietario'

    def handle(self, *args, **options):
        # Actualizar todos los superusuarios existentes
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No se encontraron superusuarios'))
            return

        for user in superusers:
            old = f'{user.username} ({user.first_name} {user.last_name})'
            user.first_name = 'Jerson Ernesto'
            user.last_name  = 'Chura Pacci'
            if 'juan' in user.email.lower() or not user.email or 'admin' in user.email.lower():
                user.email = 'echurapacci@gmail.com'
            user.username = 'jersonchura'
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Actualizado: {old} → {user.username} ({user.first_name} {user.last_name}) <{user.email}>')
            )

        # También actualizar is_staff por email por si acaso
        self.stdout.write(self.style.SUCCESS('✓ Propietario configurado correctamente'))
