from rest_framework import serializers
from .models import Sale, Comments

class BuySerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ['slug', 'voucher', 'bitcoin_value']

class SaleListPurchaedSerializer(serializers.ModelSerializer):
    has_comment = serializers.SerializerMethodField()

    class Meta:
        model = Sale
<<<<<<< HEAD
        fields = ['accountNumber', 'reference', 'bankEntity', 'address', 'buyed_at', 'bitcoin_value', 'has_comment']
=======
        fields = ['accountNumber', 'reference', 'bankEntity', 'address', 'buyed_at', 'bitcoin_value', 'has_comment', 'status']
>>>>>>> changes

    def get_has_comment(self, obj):
        return Comments.objects.filter(sale_post=obj).exists()

class SaleGetAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

class SaleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields=[
                'bankEntity',
                'reference',
                'accountNumber'
            ]

class DashboardPostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
<<<<<<< HEAD
        fields = ('accountNumber', 'reference', 'bankEntity', 'address', 'created_at')
=======
        fields = ('accountNumber', 'reference', 'bankEntity', 'address', 'created_at', 'status', 'slug', 'voucher')
>>>>>>> changes
        
class EditeSaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ['bankEntity', 'reference', 'accountNumber']

class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comments
        fields=[
                'sale_post',
                'text'
            ]