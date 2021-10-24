from django.contrib import admin

from .models import Response, Trigger


class ResponseInline(admin.TabularInline):
    model = Response


@admin.register(Trigger)
class TriggerADmin(admin.ModelAdmin):
    inlines = (ResponseInline,)
    list_display = ('phrase',)
    search_fields = ('phrase', 'responses__say')
