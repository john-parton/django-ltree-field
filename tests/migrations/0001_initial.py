# Generated by Django 3.1.7 on 2021-03-29 01:59

import django.contrib.postgres.operations
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        django.contrib.postgres.operations.CreateExtension(
            name="ltree",
        )
    ]
