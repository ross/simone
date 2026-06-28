from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'workspace',
        'user_id',
        'sparkles',
        'updated_at',
        'created_at',
    )
    list_filter = ('workspace',)
    ordering = ('workspace', '-sparkles')
    search_fields = ('user_id',)
