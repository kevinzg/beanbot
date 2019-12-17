from django.conf import settings
from django.db import models

from beanbot.ledger.constants import COMPLETE, INCOMPLETE

User = settings.AUTH_USER_MODEL


class BaseTransaction(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    date = models.DateField()
    payee = models.ForeignKey(
        'Payee',
        on_delete=models.PROTECT,
        null=True,
        related_name='+',
    )
    narration = models.TextField(
        blank=True,
    )
    flag = models.CharField(
        max_length=1,
        default=INCOMPLETE,
        choices=[
            (INCOMPLETE, '!'),
            (COMPLETE, '*'),
        ]
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date', '-created_at']),
        ]


class BasePosting(models.Model):
    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='+',
    )
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=4,
    )
    explicit = models.BooleanField(
        default=True,
    )

    class Meta:
        abstract = True

    @property
    def is_target(self):
        return self.explicit

    @property
    def is_source(self):
        return not self.is_target


class Transaction(BaseTransaction):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        related_query_name='transaction'
    )


class Posting(BasePosting):
    transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
        related_name='postings',
        related_query_name='posting',
    )


class TransactionTemplate(BaseTransaction):
    keyword = models.TextField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='templates',
        related_query_name='template'
    )

    class Meta(BaseTransaction.Meta):
        unique_together = ['user', 'keyword']


class PostingTemplate(BasePosting):
    transaction = models.ForeignKey(
        'TransactionTemplate',
        on_delete=models.CASCADE,
        related_name='postings',
        related_query_name='posting',
    )
