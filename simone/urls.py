from django.contrib import admin
from django.urls import path

from slacker.urls import slack_events_handler

urlpatterns = [
    path("slack/events", slack_events_handler, name="slack_events"),
    path('admin/', admin.site.urls),
]
