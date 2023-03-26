# Generated by Django 4.0.1 on 2022-06-13 21:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('slotter', '0007_section_class_end_time_section_class_start_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='section',
            name='class_days',
            field=models.CharField(choices=[('MW', 'Monday/Wednesday'), ('TR', 'Tuesday/Thursday')], default='MW', max_length=3),
        ),
        migrations.CreateModel(
            name='Timeslot_Combos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='slotter.section')),
                ('timeslots', models.ManyToManyField(to='slotter.Timeslot')),
            ],
        ),
    ]
