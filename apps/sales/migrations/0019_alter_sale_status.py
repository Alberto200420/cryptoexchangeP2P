# Generated by Django 5.0.1 on 2024-03-27 00:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0018_alter_sale_country_alter_sale_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('paused', 'Paused'), ('pending', 'Pending'), ('taked_offer', 'Taked offer'), ('reported', 'Reported'), ('bought', 'Bought')], default='pending', max_length=11),
        ),
    ]
