from django.conf import settings
from django.db import models
from djoser.signals import user_registered
User = settings.AUTH_USER_MODEL

class Profile(models.Model):
  user =                     models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
  postsCreated =             models.PositiveIntegerField(default=0)
  number_of_sales =          models.PositiveIntegerField(default=0)
  number_of_purchase =       models.PositiveIntegerField(default=0)
  successful_exchanges =     models.PositiveIntegerField(default=0)
  reports =                  models.PositiveIntegerField(default=0)

def post_user_registered(request, user, *args, **kwargs):
  user = user
  Profile.objects.create(user=user)

user_registered.connect(post_user_registered)