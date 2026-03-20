import uuid
from datetime import datetime, timedelta

from django.db import models


class Customer(models.Model):
    """Cliente del negocio — no necesita cuenta en el SaaS."""

    tenant     = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='customers')
    name       = models.CharField(max_length=200)
    phone      = models.CharField(max_length=20)
    email      = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.phone}'


class Booking(models.Model):
    STATUS = [
        ('pending',   'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada'),
        ('completed', 'Completada'),
        ('no_show',   'No se presentó'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant     = models.ForeignKey('tenants.Tenant',   on_delete=models.CASCADE,  related_name='bookings')
    customer   = models.ForeignKey(Customer,           on_delete=models.CASCADE,  related_name='bookings')
    service    = models.ForeignKey('services.Service', on_delete=models.CASCADE,  related_name='bookings')
    staff      = models.ForeignKey('services.Staff',   on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')

    date       = models.DateField()
    start_time = models.TimeField()
    end_time   = models.TimeField()
    status     = models.CharField(max_length=20, choices=STATUS, default='pending')
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering            = ['-date', '-start_time']
        unique_together     = ['tenant', 'staff', 'date', 'start_time']

    def save(self, *args, **kwargs):
        """
        Auto-calcula end_time = start_time + service.duration.
        Garantiza consistencia aunque end_time no se pase explícitamente.
        """
        update_fields = kwargs.get('update_fields')
        should_recalc = not update_fields or (
            'start_time' in update_fields or 'service' in update_fields
        )
        if should_recalc and self.start_time and self.service_id:
            self.end_time = (
                datetime.combine(self.date, self.start_time)
                + timedelta(minutes=self.service.duration)
            ).time()
            # Si se usó update_fields, asegurar que end_time queda incluido
            if update_fields and 'end_time' not in update_fields:
                kwargs['update_fields'] = list(update_fields) + ['end_time']
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.customer.name} — {self.service.name} — {self.date} {self.start_time}'
