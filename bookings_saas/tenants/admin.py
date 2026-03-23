"""
tenants/admin.py
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Tenant, TenantUser, Payment, TenantNote, SystemConfig


class TenantUserInline(admin.TabularInline):
    model      = TenantUser
    extra      = 0
    fields     = ['user', 'role', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display   = ['name', 'business_type', 'city', 'plan_badge', 'status_badge', 'created_at']
    list_filter    = ['business_type', 'plan', 'is_active', 'city']
    search_fields  = ['name', 'email', 'phone', 'slug']
    readonly_fields = ['id', 'slug', 'created_at', 'updated_at']
    prepopulated_fields = {}  # slug es auto-generado en el modelo
    inlines        = [TenantUserInline]

    fieldsets = (
        ('Identidad', {
            'fields': ('id', 'name', 'slug', 'business_type', 'logo'),
        }),
        ('Contacto', {
            'fields': ('phone', 'email', 'address', 'city'),
        }),
        ('Plan y estado', {
            'fields': ('plan', 'is_active'),
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Plan')
    def plan_badge(self, obj):
        colors = {'basic': '#3b82f6', 'pro': '#8b5cf6'}
        color  = colors.get(obj.plan, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9999px;font-size:11px">{}</span>',
            color, obj.get_plan_display(),
        )

    @admin.display(description='Estado')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:9999px;font-size:11px">Activo</span>'
            )
        return format_html(
            '<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:9999px;font-size:11px">Inactivo</span>'
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'amount', 'method', 'paid_at', 'period_month', 'period_year', 'created_by']
    list_filter   = ['method', 'period_year']
    search_fields = ['tenant__name', 'reference']
    raw_id_fields = ['tenant', 'created_by']


@admin.register(TenantNote)
class TenantNoteAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'created_by', 'created_at', 'content_preview']
    raw_id_fields = ['tenant', 'created_by']

    @admin.display(description='Contenido')
    def content_preview(self, obj):
        return obj.content[:80]


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value_preview', 'updated_at']

    @admin.display(description='Valor')
    def value_preview(self, obj):
        return obj.value[:60]


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display   = ['full_name', 'email', 'tenant', 'role_badge', 'created_at']
    list_filter    = ['role', 'tenant__city']
    search_fields  = ['user__username', 'user__email', 'user__first_name', 'tenant__name']
    readonly_fields = ['created_at']
    raw_id_fields   = ['user', 'tenant']

    @admin.display(description='Nombre')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email

    @admin.display(description='Rol')
    def role_badge(self, obj):
        color = '#f59e0b' if obj.role == 'owner' else '#6b7280'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9999px;font-size:11px">{}</span>',
            color, obj.get_role_display(),
        )
