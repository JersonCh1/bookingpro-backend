"""
bookings/tasks.py
──────────────────
Tareas periódicas para notificaciones automáticas.

Sin Celery: llamar con `python manage.py run_tasks`
Con Celery: registrar en CELERY_BEAT_SCHEDULE en settings/base.py
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def send_reminder_24h():
    """
    Block 4 — Recordatorio 24h antes de la cita.
    Busca reservas de mañana, pendientes/confirmadas, sin recordatorio enviado.
    """
    from .models import Booking
    from bookings_saas.notifications.services import send_booking_reminder_with_token

    tomorrow = timezone.now().date() + timedelta(days=1)
    bookings = Booking.objects.filter(
        date=tomorrow,
        status__in=['pending', 'confirmed'],
        reminder_sent=False,
    ).select_related('customer', 'service', 'tenant')

    sent = 0
    for booking in bookings:
        try:
            send_booking_reminder_with_token(booking)
            booking.reminder_sent = True
            booking.save(update_fields=['reminder_sent'])
            sent += 1
        except Exception as e:
            logger.warning('Error enviando recordatorio booking %s: %s', booking.id, e)

    logger.info('Recordatorios 24h enviados: %d', sent)
    return sent


def send_rating_requests():
    """
    Block 5 — Solicitud de valoración post-servicio.
    Busca bookings completados hace 2-24h, sin solicitud enviada.
    """
    from .models import Booking
    from bookings_saas.notifications.whatsapp import send_whatsapp

    now       = timezone.now()
    two_hours = now - timedelta(hours=2)
    one_day   = now - timedelta(hours=24)

    bookings = Booking.objects.filter(
        status='completed',
        rating_requested=False,
    ).select_related('customer', 'service', 'tenant')

    sent = 0
    for booking in bookings:
        try:
            # Aproximar hora de finalización: combinar fecha + end_time
            from django.utils import timezone as tz
            import datetime
            end_dt = tz.make_aware(
                datetime.datetime.combine(booking.date, booking.end_time)
            )
            if not (one_day <= end_dt <= two_hours):
                continue

            customer = booking.customer
            tenant   = booking.tenant
            if not customer.phone:
                continue

            frontend_url = _get_frontend_url()
            msg = (
                f'Hola {customer.name.split()[0]} ⭐\n\n'
                f'¿Cómo fue tu experiencia en *{tenant.name}*?\n\n'
                f'Puntúa del 1 al 5 aquí (tarda 10 segundos):\n'
                f'{frontend_url}/valorar/{booking.cancel_token}\n\n'
                f'¡Tu opinión nos ayuda mucho! 🙏'
            )
            send_whatsapp(customer.phone, msg)
            booking.rating_requested = True
            booking.save(update_fields=['rating_requested'])
            sent += 1
        except Exception as e:
            logger.warning('Error enviando solicitud de rating booking %s: %s', booking.id, e)

    logger.info('Solicitudes de rating enviadas: %d', sent)
    return sent


def send_daily_summary():
    """
    Block 11 — Resumen diario al negocio (enviar a las 7:30am).
    Solo para tenants activos con citas hoy.
    """
    from .models import Booking
    from bookings_saas.tenants.models import Tenant
    from bookings_saas.notifications.whatsapp import send_whatsapp
    from django.db.models import Sum

    today      = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())

    active_tenants = Tenant.objects.filter(is_active=True)
    sent = 0

    for tenant in active_tenants:
        if not tenant.phone:
            continue

        todays_bookings = Booking.objects.filter(
            tenant=tenant,
            date=today,
            status__in=['pending', 'confirmed'],
        ).select_related('customer', 'service').order_by('start_time')

        if not todays_bookings.exists():
            continue  # No molestar si no hay citas

        # Estadísticas de la semana
        week_completed = Booking.objects.filter(
            tenant=tenant,
            date__gte=week_start,
            status='completed',
        )
        week_count   = week_completed.count()
        week_revenue = float(week_completed.aggregate(t=Sum('service__price'))['t'] or 0)

        lines = []
        for b in todays_bookings:
            hour = b.start_time.strftime('%I:%M %p').lstrip('0')
            lines.append(f'  🕐 {hour} — {b.customer.name} ({b.service.name})')

        citas_list = '\n'.join(lines)
        n = todays_bookings.count()

        msg = (
            f'Buenos días {tenant.name} ☀️\n\n'
            f'Hoy tienes *{n}* cita{"s" if n != 1 else ""}:\n'
            f'{citas_list}\n\n'
            f'📊 Esta semana: {week_count} citas completadas\n'
            f'💰 Ingresos semana: S/. {week_revenue:.0f}\n\n'
            f'— AgendaYa 🗓'
        )

        try:
            send_whatsapp(tenant.phone, msg)
            sent += 1
        except Exception as e:
            logger.warning('Error enviando resumen diario a %s: %s', tenant.name, e)

    logger.info('Resúmenes diarios enviados: %d', sent)
    return sent


def _get_frontend_url():
    from django.conf import settings
    return getattr(settings, 'FRONTEND_URL', 'https://agendaya.online')
