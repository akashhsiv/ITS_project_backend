# Generated by Django 5.2.3 on 2025-06-27 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('features', '0004_remove_item_menus_item_menus'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='charges',
        ),
        migrations.RemoveField(
            model_name='item',
            name='tags',
        ),
        migrations.AddField(
            model_name='item',
            name='charges',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='item',
            name='tags',
            field=models.TextField(blank=True),
        ),
    ]
