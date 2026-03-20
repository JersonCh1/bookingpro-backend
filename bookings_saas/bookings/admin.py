from django.contrib import admin
from django.utils.html import format_html

from .models import Customer, Booking

STATUS_COLORS = {
    'pending':   ('#d97706', '#fef3c7'),   # amber
    'confirmed': ('#1d4ed8', '#dbeafe'),   # blue
    'completed': ('#15803d', '#dcfce7'),   # green
    'cancelled': ('#b91c1c', '#fee2e2'),   # red
    'no_show':   ('#6b7280', '#f3f4f6'),   # gray
}


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ['name', 'phone', 'email', 'tenant', 'booking_count', 'created_at']
    search_fields = ['name', 'phone', 'email']
    list_filter   = ['tenant']
    list_per_page = 30

    @admin.display(description='Reservas')
    def booking_count(self, obj):
        return obj.bookings.count()


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display    = ['customer_display', 'service_display', 'date', 'time_display', 'staff_display', 'status_badge', 'tenant']
    list_filter     = ['status', 'tenant', 'date']
    search_fields   = ['customer__name', 'customer__phone', 'service__name']
    readonly_fields = ['id', 'end_time', 'created_at']
    date_hierarchy  = 'date'
    list_per_page   = 30
    ordering        = ['-date', 'start_time']

    @admin.display(description='Cliente')
    def customer_display(self, obj):
        return f'{obj.customer.name} ({obj.customer.phone})'

    @admin.display(description='Servicio')
    def service_display(self, obj):
        return f'{obj.service.name} · S/. {obj.service.price}'

    @admin.display(description='Hora')
    def time_display(self, obj):
        return f'{obj.start_time.strftime("%H:%M")} – {obj.end_time.strftime("%H:%M")}'

    @admin.display(description='Empleado')
    def staff_display(self, obj):
        return obj.staff.name if obj.staff else '—'

    @admin.display(description='Estado')
    def status_badge(self, obj):
        color, bg = STATUS_COLORS.get(obj.status, ('#374151', '#f9fafb'))
        label = dict(Booking.STATUS).get(obj.status, obj.status)
        return format_html(
            '<span style="color:{};background:{};padding:2px 8px;border-radius:9999px;font-size:12px;font-weight:600">{}</span>',
            color, bg, label,
        )
