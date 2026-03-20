from django.db import models


class Service(models.Model):
    tenant      = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='services')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration    = models.IntegerField(help_text='Duración en minutos')
    price       = models.DecimalField(max_digits=8, decimal_places=2)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering            = ['name']

    def __str__(self):
        return f'{self.name} ({self.tenant.name})'


class Staff(models.Model):
    tenant     = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='staff')
    name       = models.CharField(max_length=200)
    phone      = models.CharField(max_length=20, blank=True)
    services   = models.ManyToManyField(Service, blank=True, related_name='staff_members')
    is_active  = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f'{self.name} — {self.tenant.name}'
