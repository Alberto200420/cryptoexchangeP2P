# Generated by Django 5.0.1 on 2024-03-10 05:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_remove_useraccount_verified_alter_useraccount_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useraccount',
            name='role',
            field=models.CharField(choices=[('user_basic', 'User_basic'), ('owner', 'Owner'), ('moderator', 'Moderator')], default='user_basic', max_length=25),
        ),
    ]
