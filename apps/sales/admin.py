from django.contrib import admin
from .models import Sale, Comments

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'address', 'created_at')
    list_filter = ('status' ,)
    search_fields = ('user__email', 'slug', 'address')
    readonly_fields = ('user', 'accountNumber')  # Campos que no se pueden editar desde el admin

@admin.register(Comments)
class CommentsAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale_post', 'user', 'text')
    list_filter = ('sale_post', 'user')
    search_fields = ('sale_post__id', 'user__username', 'text')
    ordering = ('-id',)