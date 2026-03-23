"""
tenants/serializers.py
"""
import re
import logging
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers
from .models import Tenant, TenantUser

logger = logging.getLogger('bookings_saas')


# ── Tenant ────────────────────────────────────────────────

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Tenant
        fields = [
            'id', 'name', 'slug', 'business_type',
            'logo', 'phone', 'email', 'address', 'city', 'description',
            'is_active', 'plan', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'plan', 'is_active', 'created_at', 'updated_at']

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('El nombre debe tener al menos 2 caracteres.')
        return value.strip()

    def validate_phone(self, value):
        cleaned = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^(\+51)?9\d{8}$', cleaned):
            raise serializers.ValidationError('Ingresa un número de WhatsApp peruano válido (9 dígitos).')
        return value


class TenantPublicSerializer(serializers.ModelSerializer):
    """Solo campos públicos — para la página de reservas."""
    class Meta:
        model  = Tenant
        fields = [
            'id', 'name', 'slug', 'business_type',
            'logo', 'phone', 'address', 'city', 'description',
        ]


# ── User ──────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    role        = serializers.CharField(source='tenant_user.role', read_only=True)
    tenant_id   = serializers.SerializerMethodField()
    tenant_slug = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name',
            'is_staff',
            'role', 'tenant_id', 'tenant_slug',
        ]

    def get_tenant_id(self, obj):
        try:
            return str(obj.tenant_user.tenant.id)
        except AttributeError:
            return None

    def get_tenant_slug(self, obj):
        try:
            return obj.tenant_user.tenant.slug
        except AttributeError:
            return None


# ── Auth: Register ────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    # Negocio
    name          = serializers.CharField(max_length=200)
    business_type = serializers.CharField(max_length=100)
    phone         = serializers.CharField(max_length=20)
    email         = serializers.EmailField()
    city          = serializers.CharField(max_length=100, default='Arequipa')

    # Cuenta del owner
    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)
    password   = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este email ya está registrado.')
        return value

    def validate_name(self, value):
        return value.strip()

    def _make_username(self, email: str) -> str:
        """Genera un username único a partir del email."""
        base = re.sub(r'[^a-zA-Z0-9]', '', email.split('@')[0]) or 'user'
        base = base[:20]
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{n}'
            n += 1
        return username

    @transaction.atomic
    def create(self, validated_data):
        try:
            # 1. Crear Tenant
            tenant = Tenant.objects.create(
                name=validated_data['name'],
                business_type=validated_data['business_type'],
                phone=validated_data['phone'],
                email=validated_data['email'],
                city=validated_data.get('city', 'Arequipa'),
            )

            # 2. Horario por defecto: Lun–Vie 09:00–18:00
            #    (importación diferida para evitar circular imports)
            from bookings_saas.scheduling.models import Schedule
            for day in range(5):  # 0=Lun … 4=Vie
                Schedule.objects.create(
                    tenant=tenant,
                    day_of_week=day,
                    start_time='09:00',
                    end_time='18:00',
                )

            # 3. Crear User Django
            user = User.objects.create_user(
                username=self._make_username(validated_data['email']),
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data['first_name'].strip(),
                last_name=validated_data['last_name'].strip(),
            )

            # 4. Vincular User ↔ Tenant
            TenantUser.objects.create(user=user, tenant=tenant, role='owner')

            return user

        except Exception as e:
            logger.error('Register error: %s', e, exc_info=True)
            raise


# ── Auth: Login ───────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data['email'].lower().strip()
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Credenciales incorrectas.')

        user = authenticate(username=user_obj.username, password=data['password'])
        if not user:
            raise serializers.ValidationError('Credenciales incorrectas.')
        if not user.is_active:
            raise serializers.ValidationError('Cuenta desactivada. Contacta soporte.')

        # Los superusuarios (is_staff) pueden iniciar sesión sin tener tenant
        if not user.is_staff:
            if not hasattr(user, 'tenant_user'):
                raise serializers.ValidationError('Este usuario no tiene un negocio asociado.')
            if not user.tenant_user.tenant.is_active:
                raise serializers.ValidationError('El negocio está desactivado. Contacta soporte.')

        data['user'] = user
        return data


# ── Auth: Change Password ─────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Contraseña actual incorrecta.')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user
