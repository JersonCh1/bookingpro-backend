import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id',            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name',          models.CharField(max_length=200, verbose_name='Nombre del negocio')),
                ('slug',          models.SlugField(max_length=220, unique=True, verbose_name='URL pública')),
                ('business_type', models.CharField(max_length=100, verbose_name='Tipo de negocio')),
                ('logo',          models.ImageField(blank=True, null=True, upload_to='logos/')),
                ('phone',         models.CharField(max_length=20, verbose_name='Teléfono')),
                ('email',         models.EmailField(max_length=254, verbose_name='Email de contacto')),
                ('address',       models.TextField(blank=True, verbose_name='Dirección')),
                ('city',          models.CharField(default='Arequipa', max_length=100, verbose_name='Ciudad')),
                ('is_active',     models.BooleanField(default=True, verbose_name='Activo')),
                ('plan',          models.CharField(
                    choices=[('basic', 'Básico — S/. 80/mes'), ('pro', 'Pro   — S/. 120/mes')],
                    default='basic', max_length=20, verbose_name='Plan',
                )),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Negocio',
                'verbose_name_plural': 'Negocios',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TenantUser',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role',       models.CharField(
                    choices=[('owner', 'Propietario'), ('staff', 'Personal')],
                    default='owner', max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant',     models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='users', to='tenants.tenant',
                )),
                ('user',       models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tenant_user', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Usuario del negocio',
                'verbose_name_plural': 'Usuarios del negocio',
            },
        ),
    ]
