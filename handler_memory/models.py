from django.db import models


class Item(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
