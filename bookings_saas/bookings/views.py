from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Sum

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
    """GET /api/bookings/customers/"""
    tenant    = get_tenant(request.user)
    customers = Customer.objects.filter(tenant=tenant).order_by('-created_at')
    return success(CustomerSerializer(customers, many=True).data)
