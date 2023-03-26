# Generated by Django 4.0.1 on 2022-11-23 15:53

import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('slotter', '0020_section_spreadsheet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='section',
            name='instructor',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='section',
            name='spreadsheet',
            field=models.FileField(blank=True, null=True, storage=django.core.files.storage.FileSystemStorage(location='/spreadsheets'), upload_to=''),
        ),
    ]