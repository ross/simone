from django.db import models


class User(models.Model):
    workspace = models.ForeignKey('slacker.Workspace', on_delete=models.CASCADE)
    user_id = models.CharField(max_length=16)
    sparkles = models.IntegerField(default=0, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user_id} - {self.sparkles}'

    class Meta:
        unique_together = (('workspace', 'user_id'),)
