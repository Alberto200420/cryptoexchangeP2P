from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserAccount

class CustomUserAdmin(BaseUserAdmin):
    search_fields = ('email', 'first_name', 'last_name')
    # readonly_fields = ('id',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ("Account status", {"fields": ("is_online",)}),
        ("Role", {"fields": ("role",)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "role",
        # "verified",
    )
    ordering = ("email",)

admin.site.register(UserAccount, CustomUserAdmin)
