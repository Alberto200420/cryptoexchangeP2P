# Generated by Django 5.0.1 on 2024-03-10 06:12

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bankEntity', models.CharField(max_length=50)),
                ('country', models.CharField(choices=[('Mexico', 'mexio'), ('United_states', 'united_states'), ('Canada', 'canada')], max_length=15)),
                ('reference', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('active', 'Active'), ('paused', 'Paused'), ('Bought', 'bought')], max_length=10)),
                ('accountNumber', models.PositiveIntegerField()),
                ('cryptoAmmount', models.FloatField(blank=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='sale', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
