# Generated by Django 5.0.1 on 2024-06-01 04:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0023_sale_voucher_alter_sale_reference'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='bitcoin_value',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
