from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_payment_tenantnote_systemconfig_tenant_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='logo',
            field=models.TextField(blank=True, default=''),
        ),
    ]
