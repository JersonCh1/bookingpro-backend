"""
tenants/views.py

Endpoints:
  POST  /api/auth/register/           → crea negocio + owner → JWT + datos
  POST  /api/auth/login/              → autentica → JWT + datos
  POST  /api/auth/logout/             → invalida sesión del lado cliente
  GET   /api/auth/me/                 → usuario + tenant autenticados
  POST  /api/auth/refresh/            → renueva access token (formato consistente)
  POST  /api/auth/change-password/    → cambia contraseña

  GET   /api/tenants/me/              → datos del negocio
  PATCH /api/tenants/me/              → actualiza datos del negocio
  GET   /api/tenants/{slug}/public/   → datos públicos (sin auth)
"""
import logging
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.shortcuts import get_object_or_404

from .models import Tenant, TenantUser
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    TenantSerializer,
    TenantPublicSerializer,
    UserSerializer,
)
from .permissions import IsTenantMember, IsTenantOwner, get_tenant
from bookings_saas.utils.responses import success, error

logger = logging.getLogger('bookings_saas')


# ── Helpers internos ──────────────────────────────────────

def _build_tokens(user) -> dict:
    """Genera un par access/refresh para el usuario."""
    refresh = RefreshToken.for_user(user)
    return {
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    }


def _auth_payload(user) -> dict:
    """Payload completo de autenticación."""
    tenant = get_tenant(user)
    return {
        **_build_tokens(user),
        'user':   UserSerializer(user).data,
        'tenant': TenantSerializer(tenant).data if tenant else None,
    }


# ── Auth: Register ────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Crea un nuevo negocio + usuario owner.

    Body:
        name, business_type, phone, email, city
        first_name, last_name, password

    Retorna:
        { success, data: { access, refresh, user, tenant } }
    """
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = s.save()
    logger.info('Nuevo negocio registrado: %s', get_tenant(user).name)
    return success(data=_auth_payload(user), status=status.HTTP_201_CREATED)


# ── Auth: Login ───────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Autentica con email + password.

    Body:
        email, password

    Retorna:
        { success, data: { access, refresh, user, tenant } }
    """
    s = LoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = s.validated_data['user']
    return success(data=_auth_payload(user))


# ── Auth: Refresh ─────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Renueva el access token.

    Body:
        refresh

    Retorna:
        { success, data: { access, refresh } }
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return error('El campo refresh es requerido.', code='BAD_REQUEST',
                     status=status.HTTP_400_BAD_REQUEST)
    try:
        token      = RefreshToken(refresh_token)
        new_access = str(token.access_token)

        # Si ROTATE_REFRESH_TOKENS=True, simplejwt ya generó uno nuevo internamente
        # Usamos el mismo refresh salvo que la config lo rote
        from django.conf import settings as django_settings
        if django_settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
            token.set_jti()
            token.set_exp()
            new_refresh = str(token)
        else:
            new_refresh = refresh_token

        return success(data={'access': new_access, 'refresh': new_refresh})
    except TokenError as e:
        return error(str(e), code='TOKEN_INVALID', status=status.HTTP_401_UNAUTHORIZED)


# ── Auth: Logout ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    El cliente descarta su token.
    Aquí se puede añadir blacklisting si se activa la app en el futuro.
    """
    return success(data={'detail': 'Sesión cerrada correctamente.'})


# ── Auth: Me ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Retorna usuario autenticado + datos de su tenant.

    Retorna:
        { success, data: { user, tenant } }
    """
    tenant = get_tenant(request.user)
    return success(data={
        'user':   UserSerializer(request.user).data,
        'tenant': TenantSerializer(tenant).data if tenant else None,
    })


# ── Auth: Change Password ─────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    s = ChangePasswordSerializer(data=request.data, context={'request': request})
    s.is_valid(raise_exception=True)
    s.save()
    return success(data={'detail': 'Contraseña actualizada correctamente.'})


# ── Tenant: Me (dashboard) ────────────────────────────────

class TenantMeView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/tenants/me/   → datos del negocio
    PATCH /api/tenants/me/   → actualiza (solo owner)
    """
    serializer_class  = TenantSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsTenantOwner()]
        return [IsAuthenticated(), IsTenantMember()]

    def get_object(self):
        tenant = get_tenant(self.request.user)
        if not tenant:
            raise NotFound('No tienes un negocio asociado a esta cuenta.')
        return tenant

    def retrieve(self, request, *args, **kwargs):
        return success(data=TenantSerializer(self.get_object()).data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        s = TenantSerializer(instance, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        logger.info('Tenant actualizado: %s', instance.name)
        return success(data=s.data)


# ── Tenant: Público ───────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def tenant_public(request, slug):
    """
    GET /api/tenants/{slug}/public/
    Sin autenticación — para la página pública de reservas.
    """
    tenant = get_object_or_404(Tenant, slug=slug, is_active=True)
    return success(data=TenantPublicSerializer(tenant).data)
