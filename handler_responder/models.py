from django.db import models


class Trigger(models.Model):
    phrase = models.CharField(max_length=64, unique=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phrase


class Response(models.Model):
    trigger = models.ForeignKey(
        Trigger, on_delete=models.CASCADE, related_name='responses'
    )
    say = models.CharField(max_length=255)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.say
