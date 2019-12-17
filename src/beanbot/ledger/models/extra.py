from django.conf import settings
from django.db import models

from beanbot.ledger.constants import SOURCE, TARGET

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
        related_name='accounts',
        related_query_name='account',
    )
    default = models.CharField(
        max_length=1,
        default=None,
        null=True,
        blank=True,
        choices=[
            (SOURCE, 'Source'),
            (TARGET, 'Target'),
            (None, 'Null'),
        ]
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'name']),
        ]
        unique_together = ['user', 'default']

    def __str__(self):
        return f'[{self.id}] {self.display_name}'


class Payee(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    name = models.TextField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payees',
        related_query_name='payee',
    )
    default = models.BooleanField(
        default=None,
        null=True,
    )

    class Meta:
        unique_together = ['user', 'default']

    def __str__(self):
        return f'[{self.id}] {self.name}'
