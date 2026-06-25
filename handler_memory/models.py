from django.db import models


class Item(models.Model):
    workspace = models.ForeignKey('slacker.Workspace', on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    value = models.TextField()

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.key} - {self.value}'

    class Meta:
        unique_together = (('workspace', 'key'),)
