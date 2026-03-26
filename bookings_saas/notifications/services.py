"""
notifications/services.py
──────────────────────────
Funciones de alto nivel para enviar notificaciones de reservas.

Por cada evento se envían DOS mensajes:
  1. Al NEGOCIO  → "tienes una nueva reserva" con datos del cliente
  2. Al CLIENTE  → "tu reserva fue confirmada" con datos del negocio

Ambos envíos son asíncronos (threading daemon en whatsapp.py).
Nunca bloquean ni lanzan excepciones al llamador.
"""
import logging

from .whatsapp import send_whatsapp

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────

def _fmt_date(d) -> str:
    """Ej: 'lunes 24 de marzo de 2025'"""
    DIAS   = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    MESES  = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
               'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    return f'{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}'


def _fmt_time(t) -> str:
    """Ej: '10:30 AM'"""
    hour   = t.hour
    minute = t.strftime('%M')
    ampm   = 'AM' if hour < 12 else 'PM'
    h12    = hour % 12 or 12
    return f'{h12}:{minute} {ampm}'


def _location(tenant) -> str:
    """Dirección o ciudad del negocio."""
    return tenant.address.strip() if tenant.address and tenant.address.strip() else tenant.city


def _maps_url(tenant) -> str:
    """URL de Google Maps con la dirección del negocio."""
    import urllib.parse
    parts = [p for p in [tenant.address, tenant.city, 'Peru'] if p and p.strip()]
    return 'https://maps.google.com/?q=' + urllib.parse.quote(' '.join(parts))


# ── Mensajes de confirmación ──────────────────────────────

def _msg_negocio_nueva_reserva(booking) -> str:
    b   = booking
    biz = b.tenant
    staff_line = f'Empleado: {b.staff.name}\n' if b.staff else ''
    return (
        f'*Nueva reserva en {biz.name}*\n\n'
        f'Cliente: {b.customer.name}\n'
        f'Telefono: {b.customer.phone}\n'
        f'Servicio: {b.service.name}\n'
        f'{staff_line}'
        f'Fecha: {_fmt_date(b.date)}\n'
        f'Hora: {_fmt_time(b.start_time)}\n'
        f'Precio: S/. {b.service.price}\n\n'
        f'Notas: {b.notes or "(ninguna)"}'
    )


def _msg_cliente_confirmacion(booking) -> str:
    b   = booking
    biz = b.tenant
    staff_line = f'Con: {b.staff.name}\n' if b.staff else ''
    from django.conf import settings
    frontend   = getattr(settings, 'FRONTEND_URL', 'https://agendaya.online')
    cancel_url = f'{frontend}/cancelar/{b.cancel_token}' if getattr(b, 'cancel_token', '') else ''
    cancel_line = f'\nPara cancelar: {cancel_url}' if cancel_url else f'\nPara cancelar contactanos al {biz.phone}'
    return (
        f'*Reserva confirmada*\n\n'
        f'Hola {b.customer.name},\n'
        f'tu cita en *{biz.name}* quedo registrada.\n\n'
        f'Servicio: {b.service.name}\n'
        f'{staff_line}'
        f'Fecha: {_fmt_date(b.date)}\n'
        f'Hora: {_fmt_time(b.start_time)}\n'
        f'Precio: S/. {b.service.price}\n\n'
        f'📍 Direccion: {_location(biz)}\n'
        f'🗺 Ver en Maps: {_maps_url(biz)}\n'
        f'Telefono negocio: {biz.phone}'
        f'{cancel_line}'
    )


# ── Mensajes de cancelación ───────────────────────────────

def _msg_cliente_cancelacion(booking) -> str:
    b   = booking
    biz = b.tenant
    return (
        f'*Reserva cancelada*\n\n'
        f'Hola {b.customer.name},\n'
        f'tu cita del {_fmt_date(b.date)} a las {_fmt_time(b.start_time)} '
        f'en *{biz.name}* fue cancelada.\n\n'
        f'Para reagendar contactanos: {biz.phone}'
    )


def _msg_negocio_cancelacion(booking) -> str:
    b   = booking
    biz = b.tenant
    return (
        f'*Reserva cancelada — {biz.name}*\n\n'
        f'Cliente: {b.customer.name} ({b.customer.phone})\n'
        f'Servicio: {b.service.name}\n'
        f'Fecha: {_fmt_date(b.date)}\n'
        f'Hora: {_fmt_time(b.start_time)}'
    )


# ── Mensajes de recordatorio ──────────────────────────────

def _msg_cliente_recordatorio(booking) -> str:
    b   = booking
    biz = b.tenant
    return (
        f'*Recordatorio de cita*\n\n'
        f'Hola {b.customer.name},\n'
        f'manana tienes cita en *{biz.name}*.\n\n'
        f'Servicio: {b.service.name}\n'
        f'Hora: {_fmt_time(b.start_time)}\n'
        f'📍 Direccion: {_location(biz)}\n'
        f'🗺 Ver en Maps: {_maps_url(biz)}\n\n'
        f'Te esperamos!'
    )


# ── API pública ───────────────────────────────────────────

def send_booking_confirmation(booking) -> None:
    """
    Notifica NUEVA RESERVA a ambas partes (asíncrono).
      - Al negocio:  datos del cliente para prepararse
      - Al cliente:  confirmación con datos del negocio
    """
    biz = booking.tenant

    # 1. Al negocio (usa CALLMEBOT_API_KEY del settings)
    if biz.phone:
        send_whatsapp(biz.phone, _msg_negocio_nueva_reserva(booking))

    # 2. Al cliente (mismo apikey — CallMeBot relay)
    if booking.customer.phone:
        send_whatsapp(booking.customer.phone, _msg_cliente_confirmacion(booking))


def send_booking_cancelled(booking) -> None:
    """
    Notifica CANCELACIÓN a ambas partes (asíncrono).
    """
    biz = booking.tenant

    if booking.customer.phone:
        send_whatsapp(booking.customer.phone, _msg_cliente_cancelacion(booking))

    if biz.phone:
        send_whatsapp(biz.phone, _msg_negocio_cancelacion(booking))


def send_booking_reminder(booking) -> None:
    """
    Recordatorio 24h antes de la cita — enviar solo al cliente (asíncrono).
    Llamar desde un cron job o Celery beat.
    """
    if booking.customer.phone:
        send_whatsapp(booking.customer.phone, _msg_cliente_recordatorio(booking))


def send_booking_reminder_with_token(booking) -> None:
    """
    Recordatorio 24h — incluye link de cancelación con cancel_token.
    """
    if not booking.customer.phone:
        return
    b   = booking
    biz = b.tenant
    from django.conf import settings
    frontend   = getattr(settings, 'FRONTEND_URL', 'https://agendaya.online')
    cancel_url = f'{frontend}/cancelar/{b.cancel_token}' if getattr(b, 'cancel_token', '') else ''
    msg = (
        f'Hola {b.customer.name.split()[0]} 👋\n\n'
        f'Te recordamos tu cita *mañana*:\n\n'
        f'📍 {biz.name}\n'
        f'💈 {b.service.name}\n'
        f'🕐 {_fmt_time(b.start_time)}\n'
        f'📍 {_location(biz)}\n'
        f'🗺 {_maps_url(biz)}\n'
    )
    if cancel_url:
        msg += f'\n¿No puedes venir? Cancela aquí:\n{cancel_url}'
    send_whatsapp(b.customer.phone, msg)
