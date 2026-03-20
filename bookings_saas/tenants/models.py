"""
tenants/models.py

Modelos principales del SaaS:
  - Tenant   → cada negocio registrado
  - TenantUser → vínculo entre un User de Django y un Tenant
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
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
    logo    = models.ImageField(upload_to='logos/', null=True, blank=True)
    phone   = models.CharField(max_length=20, verbose_name='Teléfono')
    email   = models.EmailField(verbose_name='Email de contacto')
    address = models.TextField(blank=True, verbose_name='Dirección')
    city    = models.CharField(max_length=100, default='Arequipa', verbose_name='Ciudad')

    # ── Estado y plan ────────────────────────────────────
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    plan      = models.CharField(
        max_length=20, choices=PLAN_CHOICES, default='basic', verbose_name='Plan'
    )

    # ── Auditoría ────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Negocio'
        verbose_name_plural = 'Negocios'
        ordering            = ['-created_at']

    # ── Slug automático y único ───────────────────────────
    def _unique_slug(self):
        from python_slugify import slugify as py_slugify
        base = py_slugify(self.name, max_length=200)
        slug, n = base, 1
        while Tenant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
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
