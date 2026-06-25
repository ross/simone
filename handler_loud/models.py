from django.db import models


class Shout(models.Model):
    workspace = models.ForeignKey(
        'slacker.Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    text = models.CharField(max_length=255)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text

    class Meta:
        unique_together = (('workspace', 'text'),)
