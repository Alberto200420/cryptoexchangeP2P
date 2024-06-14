from django.conf import settings
from django.db import models
import uuid
User = settings.AUTH_USER_MODEL

def public_thumbnail_directory(instace, filename):
  return 'voucher/{0}/{1}'.format(instace.slug, filename)

class Sale(models.Model):

  class PostObjects(models.Manager):
    def get_queryset(self):
      return super().get_queryset().filter(status='active')

  STATUS = (
    ('active', 'Active'),
    ('paused', 'Paused'),
    ('pending', 'Pending'),
    ('looking', 'Looking'),
    ('taked_offer', 'Taked offer'),
    ('reported', 'Reported'),
    ('bought', 'Bought')
  )

  slug =          models.SlugField(max_length=255, unique=True, default=uuid.uuid4)
  user =          models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_by_user')
  bankEntity =    models.CharField(max_length=50)
  status =        models.CharField(max_length=11, choices=STATUS, default='pending')
  created_at =    models.DateTimeField(auto_now_add=True)
  accountNumber = models.PositiveIntegerField()
  buyer =         models.ForeignKey(User, 
                                    on_delete=models.SET_NULL, 
                                    null=True, blank=True,
                                    related_name='purchased_sales')
  reference =     models.CharField(max_length=100, blank=True, null=True)
  address =       models.CharField(max_length=100, unique=True)
  buyed_at =      models.DateTimeField(blank=True, null=True)
<<<<<<< HEAD
  bitcoin_value = models.IntegerField(blank=True, null=True)
=======
  bitcoin_value = models.FloatField(blank=True, null=True)
>>>>>>> changes
  voucher =       models.ImageField(upload_to=public_thumbnail_directory, blank=True, null=True)

  class Meta:
    ordering = ('-status', )

  def __str__(self):
    return self.slug
  
  def get_status(self):
    status = self.status
    return status
  
class Comments(models.Model):
  sale_post =  models.OneToOneField(Sale, on_delete=models.CASCADE, related_name='comments')
  user =       models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_commented')
  text =       models.TextField()

  def __str__(self):
    return f'Comment by {self.user} on {self.sale_post}'