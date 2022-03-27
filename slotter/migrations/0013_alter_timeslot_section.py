# Generated by Django 4.0.1 on 2022-03-25 21:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('slotter', '0012_timeslot_section'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timeslot',
            name='section',
            field=models.ForeignKey(default='Disco Elysium', on_delete=django.db.models.deletion.CASCADE, to='slotter.section'),
        ),
    ]