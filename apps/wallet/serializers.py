from rest_framework import serializers
from .models import Wallet, UTXO

class GetWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'

class GetUTXOtSerializer(serializers.ModelSerializer):
    class Meta:
        model = UTXO
        fields = '__all__'