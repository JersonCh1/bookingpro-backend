from django.db import models

DAYS = [
    (0, 'Lunes'),
    (1, 'Martes'),
    (2, 'Miércoles'),
    (3, 'Jueves'),
    (4, 'Viernes'),
    (5, 'Sábado'),
    (6, 'Domingo'),
]


class Schedule(models.Model):
    """Horario semanal del negocio o de un empleado específico."""

    tenant    = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='schedules')
    staff     = models.ForeignKey('services.Staff', null=True, blank=True, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAYS)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    is_active   = models.BooleanField(default=True)

    class Meta:
        verbose_name        = 'Horario'
        verbose_name_plural = 'Horarios'
        ordering            = ['day_of_week', 'start_time']
        unique_together     = ['tenant', 'staff', 'day_of_week']

    def __str__(self):
        staff_str = f' ({self.staff.name})' if self.staff else ''
        return f'{self.get_day_of_week_display()}{staff_str}: {self.start_time}–{self.end_time}'


class BlockedSlot(models.Model):
    """Bloquea horas específicas — feriados, descansos, vacaciones."""

    tenant     = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='blocked_slots')
    staff      = models.ForeignKey('services.Staff', null=True, blank=True, on_delete=models.CASCADE, related_name='blocked_slots')
    date       = models.DateField()
    start_time = models.TimeField()
    end_time   = models.TimeField()
    reason     = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name        = 'Slot bloqueado'
        verbose_name_plural = 'Slots bloqueados'
        ordering            = ['-date', '-start_time']

    def __str__(self):
        return f'{self.date} {self.start_time}–{self.end_time} | {self.tenant.name}'
