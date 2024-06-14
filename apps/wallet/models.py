from django.conf import settings
from django.db import models
from djoser.signals import user_registered
from apps.sales.models import Sale
User = settings.AUTH_USER_MODEL

class UTXO(models.Model):

  STATUS = (
    ('active', 'Active'),
    ('used', 'Used')
  )

  user =    models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_utxo')
  slug =    models.OneToOneField(Sale, on_delete=models.DO_NOTHING, related_name='sale_slug', unique=True)
  status =  models.CharField(max_length=6, choices=STATUS, default='active')
  address = models.CharField(max_length=100, unique=True)
  wallet =  models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='utxos')  # Relación inversa

class Wallet(models.Model):
  user =            models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_wallet')
  amountInCrypto =  models.FloatField(default=0)

def post_user_registered(request, user, *args, **kwargs):
  Wallet.objects.create(user=user)

user_registered.connect(post_user_registered)