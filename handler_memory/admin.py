from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'key', 'value', 'updated_at', 'created_at')
    list_filter = ('workspace',)
    ordering = ('workspace', 'key')
    search_fields = ('key', 'value')
