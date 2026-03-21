from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_alter_staff_options_alter_service_id_alter_staff_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='image_url',
            field=models.URLField(blank=True, default=''),
        ),
    ]
