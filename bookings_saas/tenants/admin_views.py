"""
tenants/admin_views.py

Endpoints de administración para superusuarios.
Todos protegidos con IsAdminUser (is_staff=True en Django).

Rutas montadas en /api/admin/
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from .models import Tenant
from bookings_saas.bookings.models import Booking
from bookings_saas.services.models import Service, Staff
from bookings_saas.utils.responses import success, error

logger = logging.getLogger('bookings_saas')


# ── Stats globales ────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):
    """
    GET /api/admin/stats/
    Resumen del sistema para el superadmin.
    """
    total_tenants          = Tenant.objects.count()
    active_tenants         = Tenant.objects.filter(is_active=True).count()
    total_bookings         = Booking.objects.count()
    total_revenue_estimate = active_tenants * 69

    return success(data={
        'total_tenants':          total_tenants,
        'active_tenants':         active_tenants,
        'total_bookings':         total_bookings,
        'total_revenue_estimate': total_revenue_estimate,
    })


# ── Lista de negocios ─────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_tenants(request):
    """
    GET /api/admin/tenants/?search=&city=&status=active|blocked
    Lista paginada de todos los negocios con métricas.
    """
    search        = request.query_params.get('search', '').strip()
    city_filter   = request.query_params.get('city', '').strip()
    status_filter = request.query_params.get('status', '').strip()

    qs = Tenant.objects.prefetch_related('users__user').all()

    if search:
        qs = qs.filter(name__icontains=search)
    if city_filter:
        qs = qs.filter(city__icontains=city_filter)
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'blocked':
        qs = qs.filter(is_active=False)

    result = []
    for t in qs:
        owner_email = ''
        try:
            tu = t.users.filter(role='owner').first()
            if tu:
                owner_email = tu.user.email
        except Exception:
            pass

        result.append({
            'id':             str(t.id),
            'name':           t.name,
            'slug':           t.slug,
            'business_type':  t.business_type,
            'city':           t.city,
            'phone':          t.phone,
            'email':          t.email,
            'created_at':     t.created_at.isoformat(),
            'is_active':      t.is_active,
            'owner_email':    owner_email,
            'services_count': Service.objects.filter(tenant=t).count(),
            'staff_count':    Staff.objects.filter(tenant=t).count(),
            'bookings_count': Booking.objects.filter(tenant=t).count(),
        })

    return success(data=result)


# ── Toggle activo/bloqueado ───────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_tenant_toggle(request, tenant_id):
    """
    PATCH /api/admin/tenants/{id}/toggle/
    Activa o desactiva un negocio.
    """
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND',
                     status=status.HTTP_404_NOT_FOUND)

    t.is_active = not t.is_active
    t.save(update_fields=['is_active'])
    logger.info('Admin toggle tenant %s → is_active=%s', t.name, t.is_active)
    return success(data={'id': str(t.id), 'is_active': t.is_active})


# ── Eliminar negocio ──────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def admin_tenant_delete(request, tenant_id):
    """
    DELETE /api/admin/tenants/{id}/
    Elimina el negocio y todos sus datos en cascada.
    """
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND',
                     status=status.HTTP_404_NOT_FOUND)

    name = t.name
    t.delete()
    logger.warning('Admin eliminó tenant: %s', name)
    return success(data={'detail': f'Negocio "{name}" eliminado correctamente.'})


# ── Reservas globales ─────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_bookings(request):
    """
    GET /api/admin/bookings/?page=1
    Todas las reservas del sistema con info del negocio.
    """
    page      = int(request.query_params.get('page', 1))
    page_size = 50
    offset    = (page - 1) * page_size

    total    = Booking.objects.count()
    bookings = (
        Booking.objects
        .select_related('tenant', 'customer', 'service')
        .order_by('-date', '-start_time')[offset:offset + page_size]
    )

    result = []
    for b in bookings:
        result.append({
            'id':            str(b.id),
            'tenant_name':   b.tenant.name,
            'tenant_slug':   b.tenant.slug,
            'customer_name': b.customer.name,
            'service_name':  b.service.name,
            'service_price': str(b.service.price),
            'date':          str(b.date),
            'start_time':    str(b.start_time),
            'status':        b.status,
            'created_at':    b.created_at.isoformat(),
        })

    return success(data={
        'count':   total,
        'results': result,
        'pages':   (total + page_size - 1) // page_size,
    })
