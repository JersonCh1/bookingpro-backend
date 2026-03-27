from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_service_image_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='image_url',
            field=models.TextField(blank=True, default=''),
        ),
    ]
