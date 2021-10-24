from django.db import models


class User(models.Model):
    user_id = models.CharField(max_length=16, unique=True)
    sparkles = models.IntegerField(default=0, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user_id} - {self.sparkles}'
