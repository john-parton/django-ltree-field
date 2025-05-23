# Generated by Django 5.1 on 2025-04-15 21:27

import django.contrib.postgres.indexes
from django.db import migrations, models

import django_ltree_field.constants
import django_ltree_field.fields


class Migration(migrations.Migration):
    dependencies = [
        ("test_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutoNode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "path",
                    django_ltree_field.fields.LTreeField(
                        triggers=django_ltree_field.constants.LTreeTrigger["CASCADE"]
                    ),
                ),
            ],
            options={
                "ordering": ["path"],
                "abstract": False,
                "indexes": [
                    django.contrib.postgres.indexes.GistIndex(
                        fields=["path"], name="test_app_autonode__path_idx"
                    )
                ],
            },
        ),
    ]
