# Generated by Django 4.0.1 on 2022-03-25 21:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('slotter', '0017_student_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeslot',
            name='section',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='slotter.section'),
        ),
    ]