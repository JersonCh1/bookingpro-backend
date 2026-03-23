from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_alter_customer_id'),
        ('tenants',  '0003_payment_tenantnote_systemconfig_tenant_fields'),
    ]

    operations = [
        # Block 3: cancel_token
        migrations.AddField(
            model_name='booking',
            name='cancel_token',
            field=models.CharField(blank=True, db_index=True, default='', max_length=8),
        ),
        # Block 4: reminder_sent
        migrations.AddField(
            model_name='booking',
            name='reminder_sent',
            field=models.BooleanField(default=False),
        ),
        # Block 5: rating_requested
        migrations.AddField(
            model_name='booking',
            name='rating_requested',
            field=models.BooleanField(default=False),
        ),
        # Block 5: Rating model
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score',      models.IntegerField()),
                ('comment',    models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking',    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='rating',  to='bookings.booking')),
                ('tenant',     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,    related_name='ratings', to='tenants.tenant')),
            ],
            options={
                'verbose_name':        'Valoración',
                'verbose_name_plural': 'Valoraciones',
                'ordering':            ['-created_at'],
            },
        ),
    ]
