from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at', 'created_at')
    ordering = ('key',)
    search_fields = ('key', 'value')
