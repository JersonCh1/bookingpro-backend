"""
tenants/permissions.py

Permisos y Mixin para aislamiento multi-tenant.

Regla de oro:
  NUNCA un negocio puede ver ni modificar datos de otro negocio.

Uso en views del dashboard:
    class MyView(TenantMixin, generics.ListAPIView):
        ...
        # get_tenant() disponible como self.tenant
        # get_queryset filtrará automáticamente por tenant
"""
from rest_framework.permissions import BasePermission


# ── Helpers ───────────────────────────────────────────────

def get_tenant(user):
    """
    Retorna el Tenant del usuario autenticado.
    Retorna None si el usuario no tiene TenantUser asociado.
    """
    try:
        return user.tenant_user.tenant
    except AttributeError:
        return None


def get_role(user):
    """Retorna el rol del usuario ('owner' | 'staff') o None."""
    try:
        return user.tenant_user.role
    except AttributeError:
        return None


# ── Permisos DRF ──────────────────────────────────────────

class IsTenantMember(BasePermission):
    """
    Permite acceso a cualquier usuario autenticado que pertenezca
    a un tenant activo (owner o staff).
    """
    message = 'No tienes un negocio asociado a tu cuenta.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant = get_tenant(request.user)
        return tenant is not None and tenant.is_active


class IsTenantOwner(BasePermission):
    """
    Permite acceso solo al owner del tenant.
    Usado para operaciones de escritura (crear, editar, eliminar).
    """
    message = 'Solo el propietario del negocio puede realizar esta acción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return get_role(request.user) == 'owner'

    def has_object_permission(self, request, view, obj):
        """
        Verifica que el objeto pertenece al mismo tenant del owner.
        Funciona para modelos con campo `tenant` o `business`.
        """
        tenant = get_tenant(request.user)
        if tenant is None:
            return False
        if hasattr(obj, 'tenant'):
            return obj.tenant_id == tenant.id
        if hasattr(obj, 'id') and str(obj.id) == str(tenant.id):
            return True  # el objeto ES el tenant
        return False


# ── TenantMixin ───────────────────────────────────────────

class TenantMixin:
    """
    Mixin para todas las views del dashboard.

    Garantías:
      1. `self.tenant`  → Tenant del usuario autenticado (nunca None si la vista requiere auth)
      2. Todos los querysets deben filtrarse por `tenant=self.tenant`
      3. `perform_create` automáticamente asigna el tenant al nuevo objeto

    Uso:
        class BookingListView(TenantMixin, generics.ListAPIView):
            serializer_class   = BookingSerializer
            permission_classes = [IsAuthenticated, IsTenantMember]

            def get_queryset(self):
                return Booking.objects.filter(tenant=self.tenant)
    """
    permission_classes = [IsTenantMember]   # base; views pueden extenderlo

    @property
    def tenant(self):
        """Acceso rápido al tenant. Cachea el resultado en el request."""
        if not hasattr(self, '_tenant_cache'):
            self._tenant_cache = get_tenant(self.request.user)
        return self._tenant_cache

    def get_queryset(self):
        """
        Subclases DEBEN sobreescribir esto y filtrar por `self.tenant`.
        Este default lanza un error descriptivo si se olvida.
        """
        raise NotImplementedError(
            f'{self.__class__.__name__} debe implementar get_queryset() '
            f'y filtrar por tenant=self.tenant'
        )

    def perform_create(self, serializer):
        """Inyecta el tenant al guardar cualquier nuevo objeto."""
        serializer.save(tenant=self.tenant)
