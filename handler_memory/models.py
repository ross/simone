from django.db import models


class Item(models.Model):
    team_id = models.CharField(max_length=16)
    key = models.CharField(max_length=255)
    value = models.TextField()

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('team_id', 'key'),)
