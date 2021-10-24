from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'sparkles', 'updated_at', 'created_at')
    ordering = ('-sparkles',)
    search_fields = ('user_id',)
