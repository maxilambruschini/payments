# Generated by Django 4.0.2 on 2022-02-09 14:16

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AccountInfo',
            new_name='Account',
        ),
    ]
