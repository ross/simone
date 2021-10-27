from django.db import models


class Shout(models.Model):
    text = models.CharField(max_length=255, unique=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text
