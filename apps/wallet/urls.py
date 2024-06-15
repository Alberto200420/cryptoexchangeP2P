from django.urls import path
from .views import *

urlpatterns = [
    path('get', GetWallet.as_view()),
    path('withdraw/', Withdraw.as_view())
]