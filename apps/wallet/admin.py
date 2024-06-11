from django.contrib import admin
from .models import Wallet, UTXO

@admin.register(UTXO)
class UTXOAdmin(admin.ModelAdmin):
    list_display = ('user', 'slug', 'status', 'address')
    list_filter = ('status',)
    search_fields = ('user__username', 'slug__slug')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'amountInCrypto')
    search_fields = ['user__username']