from django.db import models


class Trigger(models.Model):
    workspace = models.ForeignKey(
        'slacker.Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    phrase = models.CharField(max_length=64)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phrase

    class Meta:
        unique_together = (('workspace', 'phrase'),)


class Response(models.Model):
    trigger = models.ForeignKey(
        Trigger, on_delete=models.CASCADE, related_name='responses'
    )
    say = models.CharField(max_length=255)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.say
