from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Account(models.Model):
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


class Payee(models.Model):
    name = models.TextField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
