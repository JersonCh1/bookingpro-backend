from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_tenant_description'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Campos nuevos en Tenant ────────────────────────
        migrations.AddField(
            model_name='tenant',
            name='trial_expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Vence trial'),
        ),
        migrations.AddField(
            model_name='tenant',
            name='subscription_expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Vence suscripción'),
        ),

        # ── Modelo Payment ─────────────────────────────────
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=69, max_digits=10)),
                ('paid_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('method', models.CharField(
                    choices=[('yape', 'Yape'), ('transferencia', 'Transferencia'),
                             ('efectivo', 'Efectivo'), ('otro', 'Otro')],
                    default='yape', max_length=20,
                )),
                ('reference', models.CharField(blank=True, max_length=200)),
                ('period_month', models.IntegerField()),
                ('period_year', models.IntegerField()),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments', to='tenants.tenant',
                )),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='payments_created', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Pago',
                'verbose_name_plural': 'Pagos',
                'ordering': ['-paid_at'],
            },
        ),

        # ── Modelo TenantNote ──────────────────────────────
        migrations.CreateModel(
            name='TenantNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notes', to='tenants.tenant',
                )),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Nota interna',
                'verbose_name_plural': 'Notas internas',
                'ordering': ['-created_at'],
            },
        ),

        # ── Modelo SystemConfig ────────────────────────────
        migrations.CreateModel(
            name='SystemConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.TextField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuración',
                'verbose_name_plural': 'Configuración del sistema',
            },
        ),
    ]
