# Generated by Django 3.1.7 on 2021-03-30 03:06

from django.db import migrations, models
import django_ltree_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('test_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NullableNode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', django_ltree_field.fields.LTreeField(null=True)),
            ],
            options={
                'ordering': ['path'],
            },
        ),
        migrations.AlterModelOptions(
            name='simplenode',
            options={'ordering': ['path']},
        ),
    ]