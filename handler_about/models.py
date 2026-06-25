from django.db import models


class Fact(models.Model):
    workspace = models.ForeignKey(
        'slacker.Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    user_id = models.CharField(max_length=32)
    value = models.CharField(max_length=255)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.id} - {self.value}'

    class Meta:
        index_together = (('workspace', 'user_id', 'created_at'),)
        unique_together = (('workspace', 'user_id', 'value'),)
        ordering = ('user_id', 'created_at')
