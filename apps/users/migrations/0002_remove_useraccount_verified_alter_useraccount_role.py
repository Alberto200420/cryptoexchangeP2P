# Generated by Django 5.0.1 on 2024-03-10 05:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='useraccount',
            name='verified',
        ),
        migrations.AlterField(
            model_name='useraccount',
            name='role',
            field=models.CharField(choices=[('User_basic', 'user_basic'), ('owner', 'Owner'), ('moderator', 'Moderator')], default='user_basic', max_length=25),
        ),
    ]
