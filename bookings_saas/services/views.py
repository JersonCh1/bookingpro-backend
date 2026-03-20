from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from bookings_saas.tenants.models import Tenant
from bookings_saas.tenants.permissions import TenantMixin, IsTenantOwner
from bookings_saas.utils.responses import success
from bookings_saas.utils.views import SuccessResponseMixin

from .models import Service, Staff
from .serializers import ServiceSerializer, StaffSerializer, StaffDetailSerializer


# ── Dashboard: Services ───────────────────────────────────

class ServiceListCreateView(SuccessResponseMixin, TenantMixin, generics.ListCreateAPIView):
    """
    GET  /api/services/       → lista servicios del tenant autenticado
    POST /api/services/       → crea servicio (solo owner)
    """
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [p() for p in [*self.permission_classes, IsTenantOwner]]
        return [p() for p in self.permission_classes]

    def get_queryset(self):
        return Service.objects.filter(tenant=self.tenant)


class ServiceDetailView(SuccessResponseMixin, TenantMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/services/{id}/  → detalle
    PATCH  /api/services/{id}/  → actualizar
    DELETE /api/services/{id}/  → eliminar
    Solo owner puede modificar/eliminar.
    """
    serializer_class   = ServiceSerializer
    permission_classes = [IsTenantOwner]           # IsTenantOwner extiende IsTenantMember

    def get_queryset(self):
        return Service.objects.filter(tenant=self.tenant)


# ── Dashboard: Staff ──────────────────────────────────────

class StaffListCreateView(SuccessResponseMixin, TenantMixin, generics.ListCreateAPIView):
    """
    GET  /api/staff/   → lista empleados del tenant autenticado
    POST /api/staff/   → crea empleado (solo owner)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [p() for p in [*self.permission_classes, IsTenantOwner]]
        return [p() for p in self.permission_classes]

    def get_serializer_class(self):
        return StaffSerializer

    def get_queryset(self):
        return Staff.objects.filter(tenant=self.tenant).prefetch_related('services')


class StaffDetailView(SuccessResponseMixin, TenantMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/staff/{id}/  → detalle (incluye servicios completos)
    PATCH  /api/staff/{id}/  → actualizar
    DELETE /api/staff/{id}/  → eliminar
    Solo owner puede modificar/eliminar.
    """
    permission_classes = [IsTenantOwner]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return StaffDetailSerializer
        return StaffSerializer

    def get_queryset(self):
        return Staff.objects.filter(tenant=self.tenant).prefetch_related('services')


# ── Público: sin autenticación ────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def public_services(request, slug):
    """
    GET /api/services/public/{slug}/
    Devuelve servicios activos de un tenant público (para la página de reservas).
    """
    tenant = get_object_or_404(Tenant, slug=slug, is_active=True)
    services = Service.objects.filter(tenant=tenant, is_active=True)
    return success(ServiceSerializer(services, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_staff(request, slug):
    """
    GET /api/staff/public/{slug}/
    Devuelve empleados activos de un tenant público.
    Acepta ?service_id=X para filtrar por servicio.
    """
    tenant   = get_object_or_404(Tenant, slug=slug, is_active=True)
    queryset = Staff.objects.filter(tenant=tenant, is_active=True).prefetch_related('services')

    service_id = request.query_params.get('service_id')
    if service_id:
        queryset = queryset.filter(services__id=service_id)

    return success(StaffDetailSerializer(queryset, many=True).data)
