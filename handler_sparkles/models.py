from django.db import models


class User(models.Model):
    user_id = models.CharField(max_length=16, unique=True)
    sparkles = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
