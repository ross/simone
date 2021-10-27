from django.contrib import admin

from .models import Fact


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'value', 'updated_at', 'created_at')
    search_fields = ('user_id', 'value')
