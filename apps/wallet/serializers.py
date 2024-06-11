from rest_framework import serializers
from .models import Wallet, UTXO

class GetWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'