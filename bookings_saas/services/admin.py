from django.contrib import admin
from django.utils.html import format_html

from .models import Service, Staff


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ['name', 'tenant', 'duration_display', 'price_display', 'status_badge']
    list_filter   = ['is_active', 'tenant']
    search_fields = ['name', 'tenant__name']
    list_per_page = 25

    @admin.display(description='Duración')
    def duration_display(self, obj):
        return f'{obj.duration} min'

    @admin.display(description='Precio')
    def price_display(self, obj):
        return f'S/. {obj.price}'

    @admin.display(description='Estado')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green;font-weight:bold">● Activo</span>')
        return format_html('<span style="color:gray">● Inactivo</span>')


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display       = ['name', 'tenant', 'phone', 'services_count', 'status_badge']
    list_filter        = ['is_active', 'tenant']
    search_fields      = ['name', 'tenant__name']
    filter_horizontal  = ['services']
    list_per_page      = 25

    @admin.display(description='Servicios')
    def services_count(self, obj):
        return obj.services.count()

    @admin.display(description='Estado')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green;font-weight:bold">● Activo</span>')
        return format_html('<span style="color:gray">● Inactivo</span>')
