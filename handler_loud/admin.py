from django.contrib import admin

from .models import Shout


@admin.register(Shout)
class ShoutAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'text')
    list_filter = ('workspace',)
    ordering = ('workspace', 'text')
    search_fields = ('text',)
