# Generated by Django 5.0.1 on 2024-04-02 00:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0002_alter_profile_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='postsCreated',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
