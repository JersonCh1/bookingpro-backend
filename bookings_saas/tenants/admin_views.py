"""
tenants/admin_views.py — Endpoints Super Admin de AgendaYa
Todos protegidos con IsSuperAdmin (is_staff=True o email del dueño).
Montados en /api/admin/
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate, TruncMonth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework import status

from .models import Tenant, Payment, TenantNote, SystemConfig
from bookings_saas.bookings.models import Booking
from bookings_saas.services.models import Service, Staff
from bookings_saas.utils.responses import success, error

logger = logging.getLogger('bookings_saas')

OWNER_EMAIL = 'echurapacci'


class IsSuperAdmin(BasePermission):
    """Acceso si is_staff=True o el email contiene la firma del dueño."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or OWNER_EMAIL in (request.user.email or '')


# ── Helper ────────────────────────────────────────────────

def _tenant_data(t):
    owner_email = ''
    try:
        tu = t.users.filter(role='owner').first()
        if tu:
            owner_email = tu.user.email
    except Exception:
        pass

    return {
        'id':                     str(t.id),
        'name':                   t.name,
        'slug':                   t.slug,
        'business_type':          t.business_type,
        'city':                   t.city or '',
        'phone':                  t.phone or '',
        'email':                  t.email or '',
        'created_at':             t.created_at.isoformat(),
        'is_active':              t.is_active,
        'plan_status':            t.plan_status,
        'days_remaining':         t.days_remaining,
        'trial_expires_at':       t.trial_expires_at.isoformat() if t.trial_expires_at else None,
        'subscription_expires_at': t.subscription_expires_at.isoformat() if t.subscription_expires_at else None,
        'owner_email':            owner_email,
        'services_count':         Service.objects.filter(tenant=t).count(),
        'staff_count':            Staff.objects.filter(tenant=t).count(),
        'bookings_count':         Booking.objects.filter(tenant=t).count(),
    }


# ── Stats globales ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def admin_stats(request):
    now      = timezone.now()
    week_ago = now - timedelta(days=7)

    all_tenants     = list(Tenant.objects.all())
    active_tenants  = sum(1 for t in all_tenants if t.plan_status == 'active')
    trial_tenants   = sum(1 for t in all_tenants if t.plan_status == 'trial')
    expired_tenants = sum(1 for t in all_tenants if t.plan_status == 'expired')
    blocked_tenants = sum(1 for t in all_tenants if t.plan_status == 'blocked')
    expiring_soon   = sum(1 for t in all_tenants if t.plan_status == 'trial' and 0 <= t.days_remaining <= 2)
    new_this_week   = Tenant.objects.filter(created_at__gte=week_ago).count()
    total_bookings  = Booking.objects.count()
    total_revenue   = float(Payment.objects.aggregate(t=Sum('amount'))['t'] or 0)

    # Registros por día — últimos 30 días
    thirty_ago = now - timedelta(days=30)
    reg_qs = (
        Tenant.objects
        .filter(created_at__gte=thirty_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    registrations_by_day = [{'date': str(r['day']), 'count': r['count']} for r in reg_qs]

    # Reservas por día — últimos 14 días
    fourteen_ago = now - timedelta(days=14)
    book_qs = (
        Booking.objects
        .filter(created_at__gte=fourteen_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    bookings_by_day = [{'date': str(b['day']), 'count': b['count']} for b in book_qs]

    return success(data={
        'total_tenants':         len(all_tenants),
        'active_tenants':        active_tenants,
        'trial_tenants':         trial_tenants,
        'expired_tenants':       expired_tenants,
        'blocked_tenants':       blocked_tenants,
        'expiring_soon':         expiring_soon,
        'new_this_week':         new_this_week,
        'total_bookings':        total_bookings,
        'total_revenue':         total_revenue,
        'total_revenue_estimate': active_tenants * 69,
        'registrations_by_day':  registrations_by_day,
        'bookings_by_day':       bookings_by_day,
    })


# ── Lista de negocios ──────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def admin_tenants(request):
    search        = request.query_params.get('search', '').strip()
    city_filter   = request.query_params.get('city', '').strip()
    status_filter = request.query_params.get('status', '').strip()
    type_filter   = request.query_params.get('type', '').strip()

    qs = Tenant.objects.prefetch_related('users__user').all()

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))
    if city_filter:
        qs = qs.filter(city__icontains=city_filter)
    if type_filter:
        qs = qs.filter(business_type__icontains=type_filter)

    tenants = list(qs)

    if status_filter == 'blocked':
        tenants = [t for t in tenants if t.plan_status == 'blocked']
    elif status_filter == 'active':
        tenants = [t for t in tenants if t.plan_status == 'active']
    elif status_filter == 'trial':
        tenants = [t for t in tenants if t.plan_status == 'trial']
    elif status_filter == 'expired':
        tenants = [t for t in tenants if t.plan_status == 'expired']

    return success(data=[_tenant_data(t) for t in tenants])


# ── Detalle de un negocio ──────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def admin_tenant_detail(request, tenant_id):
    try:
        t = Tenant.objects.prefetch_related('users__user').get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)

    payments = [{
        'id':           p.id,
        'amount':       float(p.amount),
        'paid_at':      p.paid_at.isoformat(),
        'method':       p.method,
        'reference':    p.reference,
        'period_month': p.period_month,
        'period_year':  p.period_year,
        'notes':        p.notes,
    } for p in t.payments.all()[:20]]

    notes = [{
        'id':         n.id,
        'content':    n.content,
        'created_at': n.created_at.isoformat(),
        'created_by': n.created_by.email if n.created_by else '',
    } for n in t.notes.all()[:20]]

    timeline = [{'date': t.created_at.isoformat(), 'event': 'Negocio registrado'}]
    first_booking = Booking.objects.filter(tenant=t).order_by('created_at').first()
    if first_booking:
        timeline.append({'date': first_booking.created_at.isoformat(), 'event': 'Primera reserva recibida'})
    first_payment = t.payments.order_by('paid_at').first()
    if first_payment:
        timeline.append({'date': first_payment.paid_at.isoformat(), 'event': 'Primer pago registrado'})

    data = _tenant_data(t)
    data.update({
        'payments':         payments,
        'notes':            notes,
        'timeline':         sorted(timeline, key=lambda x: x['date']),
        'unique_customers': Booking.objects.filter(tenant=t).values('customer').distinct().count(),
        'total_revenue':    float(t.payments.aggregate(t=Sum('amount'))['t'] or 0),
    })
    return success(data=data)


# ── Toggle activo/bloqueado ────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def admin_tenant_toggle(request, tenant_id):
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)
    t.is_active = not t.is_active
    t.save(update_fields=['is_active'])
    logger.info('Admin toggle tenant %s → is_active=%s', t.name, t.is_active)
    return success(data={'id': str(t.id), 'is_active': t.is_active, 'plan_status': t.plan_status})


# ── Extender trial ─────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def admin_tenant_extend(request, tenant_id):
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)

    days = int(request.data.get('days', 7))
    base = t.trial_expires_at if (t.trial_expires_at and t.trial_expires_at > timezone.now()) else timezone.now()
    t.trial_expires_at = base + timedelta(days=days)
    t.is_active = True
    t.save(update_fields=['trial_expires_at', 'is_active'])
    return success(data=_tenant_data(t))


# ── Eliminar negocio ──────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def admin_tenant_delete(request, tenant_id):
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)
    name = t.name
    t.delete()
    logger.warning('Admin eliminó tenant: %s', name)
    return success(data={'detail': f'Negocio "{name}" eliminado correctamente.'})


# ── Notas internas ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def admin_tenant_add_note(request, tenant_id):
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)

    content = request.data.get('content', '').strip()
    if not content:
        return error('El contenido es requerido.', code='BAD_REQUEST', status=status.HTTP_400_BAD_REQUEST)

    note = TenantNote.objects.create(tenant=t, content=content, created_by=request.user)
    return success(data={
        'id': note.id, 'content': note.content,
        'created_at': note.created_at.isoformat(),
        'created_by': request.user.email,
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def admin_note_delete(request, note_id):
    try:
        note = TenantNote.objects.get(id=note_id)
    except TenantNote.DoesNotExist:
        return error('Nota no encontrada.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)
    note.delete()
    return success(data={'detail': 'Nota eliminada.'})


# ── Pagos ──────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def admin_payments(request):
    if request.method == 'GET':
        tenant_id = request.query_params.get('tenant_id')
        qs = Payment.objects.select_related('tenant').all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        result = [{
            'id':           p.id,
            'tenant_id':    str(p.tenant_id),
            'tenant_name':  p.tenant.name,
            'tenant_slug':  p.tenant.slug,
            'tenant_phone': p.tenant.phone or '',
            'amount':       float(p.amount),
            'paid_at':      p.paid_at.isoformat(),
            'method':       p.method,
            'reference':    p.reference,
            'period_month': p.period_month,
            'period_year':  p.period_year,
            'notes':        p.notes,
        } for p in qs[:200]]
        return success(data=result)

    # POST — registrar pago
    tenant_id = request.data.get('tenant_id')
    try:
        t = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        return error('Negocio no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    p = Payment.objects.create(
        tenant=t,
        amount=request.data.get('amount', 69),
        paid_at=request.data.get('paid_at', now.isoformat()),
        method=request.data.get('method', 'yape'),
        reference=request.data.get('reference', ''),
        period_month=request.data.get('period_month', now.month),
        period_year=request.data.get('period_year', now.year),
        notes=request.data.get('notes', ''),
        created_by=request.user,
    )

    # Activar y extender suscripción +30 días
    base = t.subscription_expires_at if (t.subscription_expires_at and t.subscription_expires_at > now) else now
    t.subscription_expires_at = base + timedelta(days=30)
    t.is_active = True
    t.save(update_fields=['subscription_expires_at', 'is_active'])

    return success(data={
        'id':                     p.id,
        'tenant_name':            t.name,
        'subscription_expires_at': t.subscription_expires_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsSuperAdmin])
def admin_payment_delete(request, payment_id):
    try:
        p = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return error('Pago no encontrado.', code='NOT_FOUND', status=status.HTTP_404_NOT_FOUND)
    p.delete()
    return success(data={'detail': 'Pago eliminado.'})


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def admin_payments_summary(request):
    now              = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_this_month = float(Payment.objects.filter(paid_at__gte=this_month_start).aggregate(t=Sum('amount'))['t'] or 0)
    total_all_time   = float(Payment.objects.aggregate(t=Sum('amount'))['t'] or 0)
    count_payments   = Payment.objects.count()

    monthly = (
        Payment.objects
        .annotate(month=TruncMonth('paid_at'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )
    by_month = [{'month': str(m['month'])[:7], 'total': float(m['total']), 'count': m['count']} for m in monthly]

    return success(data={
        'total_this_month': total_this_month,
        'total_all_time':   total_all_time,
        'avg_per_payment':  total_all_time / count_payments if count_payments else 0,
        'by_month':         by_month,
    })


# ── Reservas globales ──────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def admin_bookings(request):
    page      = int(request.query_params.get('page', 1))
    page_size = 50
    offset    = (page - 1) * page_size

    qs = Booking.objects.select_related('tenant', 'customer', 'service').order_by('-date', '-start_time')

    tenant_id     = request.query_params.get('tenant_id')
    status_filter = request.query_params.get('status')
    date_from     = request.query_params.get('date_from')
    date_to       = request.query_params.get('date_to')

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    total     = qs.count()
    completed = qs.filter(status='completed').count()
    cancelled = qs.filter(status='cancelled').count()
    no_show   = qs.filter(status='no_show').count()

    result = [{
        'id':             str(b.id),
        'tenant_name':    b.tenant.name,
        'tenant_slug':    b.tenant.slug,
        'customer_name':  b.customer.name,
        'customer_phone': getattr(b.customer, 'phone', ''),
        'service_name':   b.service.name,
        'service_price':  str(b.service.price),
        'date':           str(b.date),
        'start_time':     str(b.start_time),
        'status':         b.status,
        'created_at':     b.created_at.isoformat(),
    } for b in qs[offset:offset + page_size]]

    return success(data={
        'count':     total,
        'results':   result,
        'pages':     (total + page_size - 1) // page_size,
        'completed': completed,
        'cancelled': cancelled,
        'no_show':   no_show,
    })


# ── Configuración del sistema ──────────────────────────────

@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def admin_config(request):
    if request.method == 'GET':
        configs = SystemConfig.objects.all()
        return success(data={c.key: c.value for c in configs})

    for key, value in request.data.items():
        SystemConfig.set(key, str(value))
    return success(data={'detail': 'Configuración guardada.'})
