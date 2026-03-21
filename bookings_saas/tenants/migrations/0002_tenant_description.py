from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='description',
            field=models.TextField(blank=True, verbose_name='Descripción del negocio'),
        ),
    ]
