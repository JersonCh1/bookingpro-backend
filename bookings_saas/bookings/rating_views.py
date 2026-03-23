"""
bookings/rating_views.py
─────────────────────────
POST /api/ratings/                    → crea valoración por token de cancelación
GET  /api/tenants/{slug}/rating/      → promedio y cantidad de valoraciones
"""
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from bookings_saas.tenants.models import Tenant
from bookings_saas.utils.responses import success, error
from rest_framework import status as drf_status

from .models import Booking, Rating


@api_view(['POST'])
@permission_classes([AllowAny])
def create_rating(request):
    """
    POST /api/ratings/
    Body: { cancel_token, score (1-5), comment? }
    """
    token   = request.data.get('cancel_token', '').strip()
    score   = request.data.get('score')
    comment = request.data.get('comment', '').strip()

    if not token:
        return error('El campo cancel_token es requerido.', code='BAD_REQUEST',
                     status=drf_status.HTTP_400_BAD_REQUEST)
    if not score:
        return error('El campo score es requerido.', code='BAD_REQUEST',
                     status=drf_status.HTTP_400_BAD_REQUEST)
    try:
        score = int(score)
        if not 1 <= score <= 5:
            raise ValueError
    except (ValueError, TypeError):
        return error('El score debe ser un número entre 1 y 5.', code='INVALID_SCORE',
                     status=drf_status.HTTP_400_BAD_REQUEST)

    booking = get_object_or_404(Booking, cancel_token=token)

    if booking.status != 'completed':
        return error('Solo puedes valorar una cita completada.', code='NOT_COMPLETED',
                     status=drf_status.HTTP_400_BAD_REQUEST)

    if hasattr(booking, 'rating'):
        return error('Ya valoraste esta cita.', code='ALREADY_RATED',
                     status=drf_status.HTTP_400_BAD_REQUEST)

    rating = Rating.objects.create(
        booking=booking,
        tenant=booking.tenant,
        score=score,
        comment=comment,
    )

    return success({
        'id':      rating.id,
        'score':   rating.score,
        'comment': rating.comment,
    }, status=drf_status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def tenant_rating(request, slug):
    """
    GET /api/tenants/{slug}/rating/
    Retorna promedio y total de valoraciones del negocio.
    """
    tenant = get_object_or_404(Tenant, slug=slug, is_active=True)
    agg    = Rating.objects.filter(tenant=tenant).aggregate(
        avg=Avg('score'), total=Count('id')
    )
    reviews = Rating.objects.filter(tenant=tenant).select_related('booking__customer').order_by('-created_at')[:20]

    return success({
        'average': round(float(agg['avg'] or 0), 1),
        'total':   agg['total'] or 0,
        'reviews': [
            {
                'id':           r.id,
                'score':        r.score,
                'comment':      r.comment,
                'customer_name': r.booking.customer.name,
                'date':         str(r.created_at.date()),
            }
            for r in reviews
        ],
    })


@api_view(['GET'])
def my_tenant_rating(request):
    """
    GET /api/ratings/mine/
    Valoraciones del tenant autenticado (dashboard).
    """
    from bookings_saas.tenants.permissions import get_tenant
    from bookings_saas.tenants.permissions import IsTenantMember
    from django.db.models import Avg, Count
    tenant  = get_tenant(request.user)
    agg     = Rating.objects.filter(tenant=tenant).aggregate(avg=Avg('score'), total=Count('id'))
    reviews = Rating.objects.filter(tenant=tenant).select_related('booking__customer').order_by('-created_at')

    return success({
        'average': round(float(agg['avg'] or 0), 1),
        'total':   agg['total'] or 0,
        'reviews': [
            {
                'id':           r.id,
                'score':        r.score,
                'comment':      r.comment,
                'customer_name': r.booking.customer.name,
                'date':         str(r.created_at.date()),
                'service_name': r.booking.service.name,
            }
            for r in reviews
        ],
    })
