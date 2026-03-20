from django.contrib import admin
from django.utils.html import format_html

from .models import Schedule, BlockedSlot

DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'staff_display', 'day_display', 'hours_display', 'status_badge']
    list_filter   = ['day_of_week', 'is_active', 'tenant']
    list_per_page = 30

    @admin.display(description='Empleado')
    def staff_display(self, obj):
        return obj.staff.name if obj.staff else format_html('<em style="color:gray">Negocio</em>')

    @admin.display(description='Día')
    def day_display(self, obj):
        return obj.get_day_of_week_display()

    @admin.display(description='Horario')
    def hours_display(self, obj):
        return f'{obj.start_time.strftime("%H:%M")} – {obj.end_time.strftime("%H:%M")}'

    @admin.display(description='Estado')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green;font-weight:bold">● Activo</span>')
        return format_html('<span style="color:gray">● Inactivo</span>')


@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    list_display   = ['tenant', 'staff_display', 'date', 'hours_display', 'reason']
    list_filter    = ['tenant']
    date_hierarchy = 'date'
    list_per_page  = 30

    @admin.display(description='Empleado')
    def staff_display(self, obj):
        return obj.staff.name if obj.staff else format_html('<em style="color:gray">Negocio</em>')

    @admin.display(description='Horario')
    def hours_display(self, obj):
        return f'{obj.start_time.strftime("%H:%M")} – {obj.end_time.strftime("%H:%M")}'
