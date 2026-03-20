import uuid
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
            name='Customer',
            fields=[
                ('id',         models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',       models.CharField(max_length=200)),
                ('phone',      models.CharField(max_length=20)),
                ('email',      models.EmailField(blank=True, max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='customers',
                    to='tenants.tenant',
                )),
            ],
            options={
                'verbose_name':        'Cliente',
                'verbose_name_plural': 'Clientes',
                'ordering':            ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date',       models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time',   models.TimeField()),
                ('status',     models.CharField(
                    choices=[
                        ('pending',   'Pendiente'),
                        ('confirmed', 'Confirmada'),
                        ('cancelled', 'Cancelada'),
                        ('completed', 'Completada'),
                        ('no_show',   'No se presentó'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('notes',      models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to='bookings.customer',
                )),
                ('service', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to='services.service',
                )),
                ('staff', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='bookings',
                    to='services.staff',
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to='tenants.tenant',
                )),
            ],
            options={
                'verbose_name':        'Reserva',
                'verbose_name_plural': 'Reservas',
                'ordering':            ['-date', '-start_time'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='booking',
            unique_together={('tenant', 'staff', 'date', 'start_time')},
        ),
    ]
