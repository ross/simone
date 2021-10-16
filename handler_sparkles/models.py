from django.db import models


class User(models.Model):
    team_id = models.CharField(max_length=16)
    user_id = models.CharField(max_length=16)
    sparkles = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('team_id', 'user_id'),)
