# Generated by Django 4.0.1 on 2022-03-25 21:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('slotter', '0010_alter_student_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
            ],
        ),
    ]
