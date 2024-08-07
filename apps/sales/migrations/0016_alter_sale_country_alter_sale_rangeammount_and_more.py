# Generated by Django 5.0.1 on 2024-03-26 03:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0015_remove_sale_cryptoammount_sale_rangeammount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='country',
            field=models.CharField(choices=[('mexico', 'Mexico'), ('United_states', 'united_states'), ('canada', 'Canada')], max_length=15),
        ),
        migrations.AlterField(
            model_name='sale',
            name='rangeAmmount',
            field=models.PositiveIntegerField(default=10),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sale',
            name='status',
            field=models.CharField(choices=[('Active', 'active'), ('Paused', 'paused'), ('pending', 'Pending'), ('Taked_offer', 'taked_offer'), ('Reported', 'reported'), ('Bought', 'bought')], default='pending', max_length=11),
        ),
    ]
