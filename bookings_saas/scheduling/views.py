from datetime import datetime

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from bookings_saas.tenants.models import Tenant
from bookings_saas.tenants.permissions import TenantMixin, IsTenantOwner
from bookings_saas.utils.responses import success, error
from bookings_saas.utils.views import SuccessResponseMixin
from bookings_saas.services.models import Service, Staff

from .models import Schedule, BlockedSlot
from .serializers import ScheduleSerializer, BlockedSlotSerializer
from .services import get_available_slots, get_days_with_availability


# ── Schedule CRUD ─────────────────────────────────────────

class ScheduleListCreateView(SuccessResponseMixin, TenantMixin, generics.ListCreateAPIView):
    """
    GET  /api/scheduling/         → lista horarios del tenant
                                    ?staff_id=<id>  filtra por empleado
                                    ?staff_id=null  solo horarios del negocio
    POST /api/scheduling/         → crea horario (owner)
    """
    serializer_class = ScheduleSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsTenantOwner()]
        return [p() for p in self.permission_classes]

    def get_queryset(self):
        qs = Schedule.objects.filter(tenant=self.tenant).select_related('staff')
        staff_param = self.request.query_params.get('staff_id')
        if staff_param == 'null':
            qs = qs.filter(staff__isnull=True)
        elif staff_param:
            qs = qs.filter(staff_id=staff_param)
        return qs


class ScheduleDetailView(SuccessResponseMixin, TenantMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET   /api/scheduling/{id}/  → detalle
    PATCH /api/scheduling/{id}/  → actualizar
    DELETE /api/scheduling/{id}/ → eliminar
    """
    serializer_class   = ScheduleSerializer
    permission_classes = [IsTenantOwner]

    def get_queryset(self):
        return Schedule.objects.filter(tenant=self.tenant)


# ── BlockedSlot CRUD ──────────────────────────────────────

class BlockedSlotListCreateView(SuccessResponseMixin, TenantMixin, generics.ListCreateAPIView):
    """
    GET  /api/scheduling/blocked/   → lista bloqueos
                                      ?date=YYYY-MM-DD  filtra por fecha
    POST /api/scheduling/blocked/   → crea bloqueo (owner)
    """
    serializer_class   = BlockedSlotSerializer
    permission_classes = [IsTenantOwner]

    def get_queryset(self):
        qs = BlockedSlot.objects.filter(tenant=self.tenant).select_related('staff')
        date_param = self.request.query_params.get('date')
        if date_param:
            qs = qs.filter(date=date_param)
        return qs


class BlockedSlotDetailView(SuccessResponseMixin, TenantMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/scheduling/blocked/{id}/  → detalle
    PATCH  /api/scheduling/blocked/{id}/  → actualizar
    DELETE /api/scheduling/blocked/{id}/  → eliminar
    """
    serializer_class   = BlockedSlotSerializer
    permission_classes = [IsTenantOwner]

    def get_queryset(self):
        return BlockedSlot.objects.filter(tenant=self.tenant)


# ── Disponibilidad pública ────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def available_slots(request):
    """
    GET /api/scheduling/available-slots/
        ?tenant_slug=<slug>   (requerido)
        ?date=YYYY-MM-DD      (requerido)
        ?service_id=<int>     (requerido)
        ?staff_id=<int>       (opcional)

    Devuelve lista de slots del día con indicador de disponibilidad.
    """
    tenant_slug = request.query_params.get('tenant_slug')
    date_str    = request.query_params.get('date')
    service_id  = request.query_params.get('service_id')
    staff_id    = request.query_params.get('staff_id')

    if not all([tenant_slug, date_str, service_id]):
        return error('Parámetros requeridos: tenant_slug, date, service_id', code='MISSING_PARAMS')

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return error('Formato de fecha inválido. Usa YYYY-MM-DD', code='INVALID_DATE')

    from django.utils import timezone
    if target_date < timezone.now().date():
        return success({'date': date_str, 'slots': []})

    tenant  = get_object_or_404(Tenant,  slug=tenant_slug, is_active=True)
    service = get_object_or_404(Service, id=service_id, tenant=tenant, is_active=True)
    staff   = get_object_or_404(Staff,   id=staff_id, tenant=tenant) if staff_id else None

    slots = get_available_slots(tenant, service, target_date, staff)

    return success({
        'date':  date_str,
        'slots': [
            {'time': s['time'].strftime('%H:%M'), 'available': s['available']}
            for s in slots
        ],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def available_days(request):
    """
    GET /api/scheduling/available-days/
        ?tenant_slug=<slug>   (requerido)
        ?service_id=<int>     (requerido)
        ?year=<int>           (requerido)
        ?month=<int>          (requerido)
        ?staff_id=<int>       (opcional)

    Devuelve lista de fechas YYYY-MM-DD con al menos un slot disponible.
    Usado para resaltar días en el calendario del frontend.
    """
    tenant_slug = request.query_params.get('tenant_slug')
    service_id  = request.query_params.get('service_id')
    year_str    = request.query_params.get('year')
    month_str   = request.query_params.get('month')
    staff_id    = request.query_params.get('staff_id')

    if not all([tenant_slug, service_id, year_str, month_str]):
        return error(
            'Parámetros requeridos: tenant_slug, service_id, year, month',
            code='MISSING_PARAMS',
        )

    try:
        year  = int(year_str)
        month = int(month_str)
        if not (1 <= month <= 12):
            raise ValueError
    except ValueError:
        return error('year y month deben ser enteros válidos', code='INVALID_PARAMS')

    tenant  = get_object_or_404(Tenant,  slug=tenant_slug, is_active=True)
    service = get_object_or_404(Service, id=service_id, tenant=tenant, is_active=True)
    staff   = get_object_or_404(Staff,   id=staff_id, tenant=tenant) if staff_id else None

    days = get_days_with_availability(tenant, service, year, month, staff)

    return success({'year': year, 'month': month, 'available_days': days})
