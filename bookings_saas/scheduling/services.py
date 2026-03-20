"""
Lógica de cálculo de slots disponibles.
Separado de views.py para facilitar tests.
"""
from datetime import datetime, timedelta, date as Date

from .models import Schedule, BlockedSlot

SLOT_INTERVAL = 30  # minutos entre slots (grid de disponibilidad)


def get_available_slots(tenant, service, target_date: Date, staff=None) -> list[dict]:
    """
    Retorna lista de {'time': time_obj, 'available': bool}
    para cada slot dentro del horario del día.

    Reglas:
      1. Usa el horario del staff si existe; si no, el horario general del negocio.
      2. Un slot está ocupado si se superpone con una reserva activa (pending/confirmed).
      3. Un slot está bloqueado si cae dentro de un BlockedSlot.
      4. Cada slot dura `service.duration` minutos; el grid avanza en SLOT_INTERVAL.
    """
    weekday = target_date.weekday()  # 0=Lun … 6=Dom

    # ── 1. Obtener horario del día ─────────────────────────
    qs = Schedule.objects.filter(tenant=tenant, day_of_week=weekday, is_active=True)
    if staff:
        staff_schedule = qs.filter(staff=staff).first()
        schedule = staff_schedule or qs.filter(staff__isnull=True).first()
    else:
        schedule = qs.filter(staff__isnull=True).first()

    if not schedule:
        return []  # negocio cerrado ese día

    # ── 2. Reservas activas ese día ────────────────────────
    from bookings_saas.bookings.models import Booking
    existing = Booking.objects.filter(
        tenant=tenant,
        date=target_date,
        status__in=['pending', 'confirmed'],
    ).values('start_time', 'end_time')
    if staff:
        existing = existing.filter(staff=staff)
    existing = list(existing)  # evaluar queryset una vez

    # ── 3. Slots bloqueados ───────────────────────────────
    from django.db.models import Q
    blocked_qs = BlockedSlot.objects.filter(tenant=tenant, date=target_date)
    if staff:
        blocked_qs = blocked_qs.filter(Q(staff=staff) | Q(staff__isnull=True))
    blocked = list(blocked_qs.values('start_time', 'end_time'))

    # ── 4. Generar slots ──────────────────────────────────
    slots          = []
    service_delta  = timedelta(minutes=service.duration)
    interval       = timedelta(minutes=SLOT_INTERVAL)
    current        = datetime.combine(target_date, schedule.start_time)
    close_dt       = datetime.combine(target_date, schedule.end_time)

    while current + service_delta <= close_dt:
        slot_start = current.time()
        slot_end   = (current + service_delta).time()
        available  = True

        # Overlap con reservas existentes
        for b in existing:
            if not (slot_end <= b['start_time'] or slot_start >= b['end_time']):
                available = False
                break

        # Overlap con bloqueos
        if available:
            for bl in blocked:
                if not (slot_end <= bl['start_time'] or slot_start >= bl['end_time']):
                    available = False
                    break

        slots.append({'time': slot_start, 'available': available})
        current += interval

    return slots


def get_days_with_availability(tenant, service, year: int, month: int, staff=None) -> list[str]:
    """
    Retorna lista de fechas 'YYYY-MM-DD' que tienen al menos un slot disponible.
    Usado para resaltar días en el calendario de la página pública.
    """
    import calendar
    from datetime import date

    _, days_in_month = calendar.monthrange(year, month)
    today = date.today()
    available_days = []

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d < today:
            continue
        slots = get_available_slots(tenant, service, d, staff)
        if any(s['available'] for s in slots):
            available_days.append(d.strftime('%Y-%m-%d'))

    return available_days
