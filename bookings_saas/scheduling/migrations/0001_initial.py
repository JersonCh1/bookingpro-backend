import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants',  '0001_initial'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id',          models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.IntegerField(choices=[
                    (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
                    (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
                ])),
                ('start_time',  models.TimeField()),
                ('end_time',    models.TimeField()),
                ('is_active',   models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='schedules',
                    to='tenants.tenant',
                )),
                ('staff', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='schedules',
                    to='services.staff',
                )),
            ],
            options={
                'verbose_name':        'Horario',
                'verbose_name_plural': 'Horarios',
                'ordering':            ['day_of_week', 'start_time'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='schedule',
            unique_together={('tenant', 'staff', 'day_of_week')},
        ),
        migrations.CreateModel(
            name='BlockedSlot',
            fields=[
                ('id',         models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date',       models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time',   models.TimeField()),
                ('reason',     models.CharField(blank=True, max_length=200)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='blocked_slots',
                    to='tenants.tenant',
                )),
                ('staff', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='blocked_slots',
                    to='services.staff',
                )),
            ],
            options={
                'verbose_name':        'Slot bloqueado',
                'verbose_name_plural': 'Slots bloqueados',
            },
        ),
    ]
