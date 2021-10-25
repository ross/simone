from django.contrib import admin

from .models import Shout


@admin.register(Shout)
class ShoutAdmin(admin.ModelAdmin):
    list_display = ('text',)
    ordering = ('text',)
    search_fields = ('text',)
