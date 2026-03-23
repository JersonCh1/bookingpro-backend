from datetime import timedelta, datetime as dt

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Sum, Q

from rest_framework import generics, status as drf_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from bookings_saas.tenants.models import Tenant
from bookings_saas.tenants.permissions import TenantMixin, IsTenantMember, get_tenant
from bookings_saas.utils.responses import success, error
from bookings_saas.utils.views import SuccessResponseMixin

from .models import Customer, Booking
from .serializers import (
    BookingSerializer, BookingCreateSerializer,
    BookingStatusSerializer, CustomerSerializer,
)


def _notify(fn, booking):
    """Llama una función de notificación sin bloquear si falla."""
    try:
        fn(booking)
    except Exception:
        pass  # notificaciones son best-effort


# ── POST público + GET dashboard ─────────────────────────

class BookingListCreateView(generics.GenericAPIView):
    """
    GET  /api/bookings/  → lista reservas del tenant autenticado (dashboard)
    POST /api/bookings/  → crea reserva pública (sin auth, para clientes)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsTenantMember()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookingCreateSerializer
        return BookingSerializer

    # ── GET: dashboard ────────────────────────────────────

    def _filtered_queryset(self, tenant):
        qs = Booking.objects.filter(tenant=tenant).select_related('customer', 'service', 'staff')
        p  = self.request.query_params

        if p.get('status'):     qs = qs.filter(status=p['status'])
        if p.get('date'):       qs = qs.filter(date=p['date'])
        if p.get('date_from'):  qs = qs.filter(date__gte=p['date_from'])
        if p.get('date_to'):    qs = qs.filter(date__lte=p['date_to'])
        if p.get('staff'):      qs = qs.filter(staff_id=p['staff'])
        if p.get('service'):    qs = qs.filter(service_id=p['service'])

        search = p.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(customer__name__icontains=search) | Q(customer__phone__icontains=search)
            )
        return qs

    def get(self, request):
        tenant = get_tenant(request.user)
        qs     = self._filtered_queryset(tenant)

        page = self.paginate_queryset(qs)
        if page is not None:
            s = self.get_serializer(page, many=True)
            return self.get_paginated_response(s.data)
        return success(self.get_serializer(qs, many=True).data)

    # ── POST: público ─────────────────────────────────────

    def post(self, request):
        tenant_slug = request.data.get('tenant_slug')
        if not tenant_slug:
            return error('tenant_slug es requerido.', code='MISSING_TENANT')

        tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

        s = BookingCreateSerializer(data=request.data, context={'tenant': tenant})
        s.is_valid(raise_exception=True)
        booking = s.save()

        from bookings_saas.notifications.services import send_booking_confirmation
        _notify(send_booking_confirmation, booking)

        return success(
            BookingSerializer(booking).data,
            status=drf_status.HTTP_201_CREATED,
        )


# ── Detalle (dashboard) ───────────────────────────────────

class BookingDetailView(SuccessResponseMixin, TenantMixin, generics.RetrieveAPIView):
    """GET /api/bookings/{id}/"""
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(tenant=self.tenant).select_related('customer', 'service', 'staff')


# ── Cambiar estado (dashboard) ────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsTenantMember])
def booking_status(request, pk):
    """
    PATCH /api/bookings/{id}/status/
    Body: { "status": "confirmed" | "cancelled" | "completed" | "no_show", "notes"?: "..." }
    """
    tenant  = get_tenant(request.user)
    booking = get_object_or_404(Booking, pk=pk, tenant=tenant)

    prev_status = booking.status
    s = BookingStatusSerializer(booking, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()

    # Notificación por cancelación
    if s.validated_data.get('status') == 'cancelled' and prev_status != 'cancelled':
        from bookings_saas.notifications.services import send_booking_cancelled
        _notify(send_booking_cancelled, booking)

    booking.refresh_from_db()
    return success(BookingSerializer(booking).data)


# ── Citas de hoy (dashboard) ──────────────────────────────

@api_view(['GET'])
@permission_classes([IsTenantMember])
def bookings_today(request):
    """GET /api/bookings/today/"""
    today    = timezone.now().date()
    tenant   = get_tenant(request.user)
    bookings = (
        Booking.objects
        .filter(tenant=tenant, date=today)
        .select_related('customer', 'service', 'staff')
        .order_by('start_time')
    )
    return success(BookingSerializer(bookings, many=True).data)


# ── Estadísticas (dashboard) ──────────────────────────────

@api_view(['GET'])
@permission_classes([IsTenantMember])
def bookings_stats(request):
    """GET /api/bookings/stats/"""
    tenant      = get_tenant(request.user)
    today       = timezone.now().date()
    week_start  = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    def count_by_status(qs):
        return {
            row['status']: row['cnt']
            for row in qs.values('status').annotate(cnt=Count('id'))
        }

    today_qs = Booking.objects.filter(tenant=tenant, date=today)
    week_qs  = Booking.objects.filter(tenant=tenant, date__gte=week_start)
    month_qs = Booking.objects.filter(tenant=tenant, date__gte=month_start)

    month_revenue = (
        month_qs.filter(status='completed')
        .aggregate(total=Sum('service__price'))['total'] or 0
    )

    upcoming = (
        Booking.objects
        .filter(tenant=tenant, date__gte=today, status__in=['pending', 'confirmed'])
        .select_related('customer', 'service', 'staff')
        .order_by('date', 'start_time')[:5]
    )

    return success({
        'today': {
            'total':     today_qs.count(),
            'by_status': count_by_status(today_qs),
        },
        'week': {
            'total':     week_qs.count(),
            'by_status': count_by_status(week_qs),
        },
        'month': {
            'total':   month_qs.count(),
            'revenue': float(month_revenue),
            'by_status': count_by_status(month_qs),
        },
        'upcoming': BookingSerializer(upcoming, many=True).data,
    })


# ── Lista de clientes (dashboard) ────────────────────────

@api_view(['GET'])
@permission_classes([IsTenantMember])
def customers_list(request):
    """
    GET /api/bookings/customers/
    Retorna clientes agrupados con historial de visitas.
    """
    tenant = get_tenant(request.user)
    search = request.query_params.get('search', '').strip()

    # Obtenemos todos los bookings del tenant
    qs = (
        Booking.objects
        .filter(tenant=tenant)
        .select_related('customer', 'service')
        .order_by('-date', '-start_time')
    )
    if search:
        qs = qs.filter(
            Q(customer__name__icontains=search) | Q(customer__phone__icontains=search)
        )

    # Agrupamos por teléfono del cliente
    grouped = {}
    for b in qs:
        phone = b.customer.phone
        if phone not in grouped:
            grouped[phone] = {
                'id':            b.customer.id,
                'name':          b.customer.name,
                'phone':         phone,
                'last_visit':    None,
                'total_bookings': 0,
                'total_spent':   0.0,
                'visits':        [],
            }
        g = grouped[phone]
        g['total_bookings'] += 1
        if b.status == 'completed':
            g['total_spent'] += float(b.service.price)
        if g['last_visit'] is None or b.date > g['last_visit']:
            g['last_visit'] = b.date
        g['visits'].append({
            'id':           str(b.id),
            'date':         str(b.date),
            'start_time':   str(b.start_time),
            'service_name': b.service.name,
            'service_price': str(b.service.price),
            'status':        b.status,
        })

    result = sorted(grouped.values(), key=lambda x: x['last_visit'] or '', reverse=True)
    # Serialize dates to string
    for r in result:
        if r['last_visit']:
            r['last_visit'] = str(r['last_visit'])
    return success(result)


# ── Reservas por teléfono (público — portal cliente) ─────

@api_view(['GET'])
@permission_classes([AllowAny])
def bookings_by_phone(request):
    """
    GET /api/bookings/by-phone/?phone=987654321
    Retorna reservas futuras + recientes del cliente con ese teléfono.
    """
    phone = request.query_params.get('phone', '').strip()
    if not phone:
        return error('El parámetro phone es requerido.', code='BAD_REQUEST',
                     status=drf_status.HTTP_400_BAD_REQUEST)

    # Normalizar: quitar +, espacios, guiones
    phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')

    today    = timezone.now().date()
    # Buscar clientes que tengan este teléfono (parcial para cubrir +51)
    bookings = (
        Booking.objects
        .filter(
            Q(customer__phone__icontains=phone_clean) |
            Q(customer__phone__icontains=phone[-9:]) if len(phone_clean) >= 9 else Q(customer__phone__icontains=phone_clean),
            date__gte=today - timedelta(days=30),  # últimos 30 días + futuras
        )
        .select_related('customer', 'service', 'staff', 'tenant')
        .order_by('date', 'start_time')
    )

    data = []
    for b in bookings:
        data.append({
            'id':            str(b.id),
            'tenant_name':   b.tenant.name,
            'tenant_slug':   b.tenant.slug,
            'tenant_phone':  b.tenant.phone or '',
            'service_name':  b.service.name,
            'service_price': str(b.service.price),
            'date':          str(b.date),
            'start_time':    str(b.start_time),
            'end_time':      str(b.end_time),
            'status':        b.status,
        })

    if not data:
        return success({'bookings': [], 'found': False})
    return success({'bookings': data, 'found': True})


# ── Cancelar por teléfono (público — portal cliente) ─────

@api_view(['PATCH'])
@permission_classes([AllowAny])
def cancel_by_phone(request, pk):
    """
    PATCH /api/bookings/{id}/cancel-by-phone/
    Body: { phone }
    → verifica teléfono, verifica >2h anticipación, cancela
    """
    phone = request.data.get('phone', '').strip()
    if not phone:
        return error('El campo phone es requerido.', code='BAD_REQUEST',
                     status=drf_status.HTTP_400_BAD_REQUEST)

    booking = get_object_or_404(Booking, pk=pk)

    # Verificar teléfono
    phone_clean    = phone.replace('+', '').replace(' ', '').replace('-', '')
    customer_clean = booking.customer.phone.replace('+', '').replace(' ', '').replace('-', '')
    if phone_clean not in customer_clean and customer_clean not in phone_clean and phone_clean[-9:] not in customer_clean:
        return error('El número de teléfono no coincide.', code='PHONE_MISMATCH',
                     status=drf_status.HTTP_403_FORBIDDEN)

    if booking.status not in ('pending', 'confirmed'):
        return error('Esta reserva no se puede cancelar.', code='INVALID_STATUS',
                     status=drf_status.HTTP_400_BAD_REQUEST)

    # Verificar que faltan más de 2h
    booking_dt = timezone.make_aware(
        dt.combine(booking.date, booking.start_time)
    )
    if timezone.now() >= booking_dt - timedelta(hours=2):
        return error('No puedes cancelar con menos de 2 horas de anticipación.',
                     code='TOO_LATE', status=drf_status.HTTP_400_BAD_REQUEST)

    booking.status = 'cancelled'
    booking.save(update_fields=['status'])

    from bookings_saas.notifications.services import send_booking_cancelled
    _notify(send_booking_cancelled, booking)

    return success({'message': 'Tu cita fue cancelada. El negocio fue notificado.'})


# ── Booking por cancel_token (público) ───────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def booking_by_cancel_token(request, token):
    """
    GET /api/bookings/cancel-token/{token}/
    Retorna los detalles de la reserva asociada al token de cancelación.
    """
    booking = get_object_or_404(Booking, cancel_token=token)
    data = {
        'id':            str(booking.id),
        'cancel_token':  booking.cancel_token,
        'tenant_name':   booking.tenant.name,
        'tenant_slug':   booking.tenant.slug,
        'tenant_phone':  booking.tenant.phone or '',
        'service_name':  booking.service.name,
        'service_price': str(booking.service.price),
        'date':          str(booking.date),
        'start_time':    str(booking.start_time),
        'end_time':      str(booking.end_time),
        'status':        booking.status,
        'customer_name': booking.customer.name,
    }
    return success(data)


# ── Analytics (dashboard) ─────────────────────────────────

@api_view(['GET'])
@permission_classes([IsTenantMember])
def bookings_analytics(request):
    """GET /api/bookings/analytics/"""
    tenant      = get_tenant(request.user)
    today       = timezone.now().date()
    month_start = today.replace(day=1)
    last_month_end   = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    last_30 = today - timedelta(days=29)

    month_qs      = Booking.objects.filter(tenant=tenant, date__gte=month_start)
    last_month_qs = Booking.objects.filter(
        tenant=tenant, date__gte=last_month_start, date__lte=last_month_end
    )

    def _stats(qs):
        total    = qs.count()
        complete = qs.filter(status='completed').count()
        revenue  = float(qs.filter(status='completed').aggregate(t=Sum('service__price'))['t'] or 0)
        new_cust = qs.values('customer__phone').distinct().count()
        rate     = round(complete / total * 100) if total else 0
        return {'total': total, 'revenue': revenue, 'new_customers': new_cust, 'completion_rate': rate}

    # Reservas por día — últimos 30 días
    from django.db.models.functions import TruncDate
    bookings_by_day = (
        Booking.objects
        .filter(tenant=tenant, date__gte=last_30)
        .annotate(d=TruncDate('date'))
        .values('d')
        .annotate(count=Count('id'))
        .order_by('d')
    )
    days_data = [{'date': str(row['d']), 'count': row['count']} for row in bookings_by_day]

    # Por servicio
    by_service = (
        Booking.objects
        .filter(tenant=tenant, status='completed')
        .values('service__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    service_data = [{'name': r['service__name'], 'count': r['count']} for r in by_service]

    # Por hora
    by_hour = (
        Booking.objects
        .filter(tenant=tenant)
        .values('start_time')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    hour_data = [{'hour': str(r['start_time'])[:5], 'count': r['count']} for r in by_hour]

    # Top clientes
    top_customers = (
        Booking.objects
        .filter(tenant=tenant)
        .values('customer__name', 'customer__phone')
        .annotate(visits=Count('id'))
        .order_by('-visits')[:5]
    )
    top_data = [
        {'name': r['customer__name'], 'phone': r['customer__phone'], 'visits': r['visits']}
        for r in top_customers
    ]

    return success({
        'this_month_stats':  _stats(month_qs),
        'last_month_stats':  _stats(last_month_qs),
        'bookings_by_day':   days_data,
        'bookings_by_service': service_data,
        'bookings_by_hour':  hour_data,
        'top_customers':     top_data,
    })
