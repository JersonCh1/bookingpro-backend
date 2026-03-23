from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0002_alter_blockedslot_options_alter_blockedslot_id_and_more'),
    ]

    operations = [
        # Block 7: all_day flag
        migrations.AddField(
            model_name='blockedslot',
            name='all_day',
            field=models.BooleanField(default=False),
        ),
        # Make start_time / end_time nullable for all-day blocks
        migrations.AlterField(
            model_name='blockedslot',
            name='start_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='blockedslot',
            name='end_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
