from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'number_of_sales', 'number_of_purchase', 'successful_exchanges', 'reports', 'postsCreated')
    search_fields = ('user__username', 'user__email')  # Puedes ajustar estos campos según tus necesidades