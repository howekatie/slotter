# Generated by Django 4.0.1 on 2022-09-24 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('slotter', '0019_section_quarter'),
    ]

    operations = [
        migrations.AddField(
            model_name='section',
            name='spreadsheet',
            field=models.FileField(blank=True, null=True, upload_to=''),
        ),
    ]
