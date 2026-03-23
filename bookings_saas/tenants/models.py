"""
tenants/models.py

Modelos principales del SaaS:
  - Tenant   → cada negocio registrado
  - TenantUser → vínculo entre un User de Django y un Tenant
"""
import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify


class Tenant(models.Model):

    PLAN_CHOICES = [
        ('basic', 'Básico — S/. 80/mes'),
        ('pro',   'Pro   — S/. 120/mes'),
    ]

    # ── Identidad ────────────────────────────────────────
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name          = models.CharField(max_length=200, verbose_name='Nombre del negocio')
    slug          = models.SlugField(max_length=220, unique=True, verbose_name='URL pública')
    business_type = models.CharField(max_length=100, verbose_name='Tipo de negocio')
    # Ejemplos: "salon", "barberia", "spa", "consultorio", "gym", "estudio"

    # ── Contacto ─────────────────────────────────────────
    logo        = models.ImageField(upload_to='logos/', null=True, blank=True)
    phone       = models.CharField(max_length=20, verbose_name='Teléfono')
    email       = models.EmailField(verbose_name='Email de contacto')
    address     = models.TextField(blank=True, verbose_name='Dirección')
    city        = models.CharField(max_length=100, default='Arequipa', verbose_name='Ciudad')
    description = models.TextField(blank=True, verbose_name='Descripción del negocio')

    # ── Estado y plan ────────────────────────────────────
    is_active               = models.BooleanField(default=True, verbose_name='Activo')
    plan                    = models.CharField(
        max_length=20, choices=PLAN_CHOICES, default='basic', verbose_name='Plan'
    )
    trial_expires_at        = models.DateTimeField(null=True, blank=True, verbose_name='Vence trial')
    subscription_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Vence suscripción')

    # ── Auditoría ────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Negocio'
        verbose_name_plural = 'Negocios'
        ordering            = ['-created_at']

    # ── Slug automático y único ───────────────────────────
    def _unique_slug(self):
        from slugify import slugify as py_slugify
        base = py_slugify(self.name, max_length=200)
        slug, n = base, 1
        while Tenant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    @property
    def plan_status(self):
        now = timezone.now()
        if not self.is_active:
            return 'blocked'
        if self.subscription_expires_at and self.subscription_expires_at > now:
            return 'active'
        if self.trial_expires_at and self.trial_expires_at > now:
            return 'trial'
        if self.trial_expires_at and self.trial_expires_at <= now:
            return 'expired'
        return 'trial'

    @property
    def days_remaining(self):
        now = timezone.now()
        if self.subscription_expires_at and self.subscription_expires_at > now:
            return max(0, (self.subscription_expires_at - now).days)
        if self.trial_expires_at and self.trial_expires_at > now:
            return max(0, (self.trial_expires_at - now).days)
        return 0

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        if not self.pk and not self.trial_expires_at:
            self.trial_expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.city})'


class TenantUser(models.Model):
    """
    Vínculo User ↔ Tenant.
    Un User de Django solo puede pertenecer a UN Tenant (OneToOne).
    """

    ROLE_CHOICES = [
        ('owner', 'Propietario'),
        ('staff', 'Personal'),
    ]

    user       = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='tenant_user'
    )
    tenant     = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='users'
    )
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Usuario del negocio'
        verbose_name_plural = 'Usuarios del negocio'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} — {self.tenant.name} [{self.role}]'

    # ── Helpers de conveniencia ───────────────────────────
    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username


class Payment(models.Model):
    """Registro de pagos de suscripción por negocio."""
    METHOD_CHOICES = [
        ('yape', 'Yape'),
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
        ('otro', 'Otro'),
    ]
    tenant       = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payments')
    amount       = models.DecimalField(max_digits=10, decimal_places=2, default=69)
    paid_at      = models.DateTimeField(default=timezone.now)
    method       = models.CharField(max_length=20, choices=METHOD_CHOICES, default='yape')
    reference    = models.CharField(max_length=200, blank=True)
    period_month = models.IntegerField()
    period_year  = models.IntegerField()
    notes        = models.TextField(blank=True)
    created_by   = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, related_name='payments_created'
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-paid_at']
        verbose_name        = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f'{self.tenant.name} — S/. {self.amount} ({self.paid_at.strftime("%m/%Y")})'


class TenantNote(models.Model):
    """Notas internas del superadmin sobre un negocio."""
    tenant     = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='notes')
    content    = models.TextField()
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Nota interna'
        verbose_name_plural = 'Notas internas'

    def __str__(self):
        return f'Nota sobre {self.tenant.name} ({self.created_at.date()})'


class SystemConfig(models.Model):
    """Configuración global del sistema AgendaYa."""
    key        = models.CharField(max_length=100, unique=True)
    value      = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Configuración'
        verbose_name_plural = 'Configuración del sistema'

    def __str__(self):
        return f'{self.key} = {self.value[:50]}'

    @classmethod
    def get(cls, key, default=''):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.update_or_create(key=key, defaults={'value': str(value)})
        return obj
