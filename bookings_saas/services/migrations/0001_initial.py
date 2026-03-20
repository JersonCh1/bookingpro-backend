import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id',          models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',        models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('duration',    models.IntegerField(help_text='Duración en minutos')),
                ('price',       models.DecimalField(decimal_places=2, max_digits=8)),
                ('is_active',   models.BooleanField(default=True)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='services',
                    to='tenants.tenant',
                )),
            ],
            options={
                'verbose_name':        'Servicio',
                'verbose_name_plural': 'Servicios',
                'ordering':            ['name'],
            },
        ),
        migrations.CreateModel(
            name='Staff',
            fields=[
                ('id',        models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name',      models.CharField(max_length=200)),
                ('phone',     models.CharField(blank=True, max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='staff',
                    to='tenants.tenant',
                )),
                ('services', models.ManyToManyField(
                    blank=True,
                    related_name='staff_members',
                    to='services.service',
                )),
            ],
            options={
                'verbose_name':        'Empleado',
                'verbose_name_plural': 'Empleados',
            },
        ),
    ]
