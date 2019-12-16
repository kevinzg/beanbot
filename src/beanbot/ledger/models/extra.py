from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Account(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    name = models.TextField()
    display_name = models.TextField()
    initial_amount = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        default=0,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    default = models.CharField(
        max_length=1,
        default=None,
        null=True,
        blank=True,
        choices=[
            ('s', 'Source'),
            ('t', 'Target'),
            (None, 'Null'),
        ]
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'name']),
        ]
        unique_together = ['user', 'default']


class Payee(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    name = models.TextField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    default = models.BooleanField(
        default=None,
        null=True,
    )

    class Meta:
        unique_together = ['user', 'default']
