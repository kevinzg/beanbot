from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class BaseTransaction(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    date = models.DateField(
        auto_now_add=True,
    )
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
        default='!',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )


class BasePosting(models.Model):
    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='+',
    )
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
    )
    explicit = models.BooleanField(
        default=False,
    )


class Transaction(BaseTransaction):
    pass


class Posting(BasePosting):
    transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.CASCADE,
    )


class TransactionTemplate(BaseTransaction):
    keyword = models.TextField()

    class Meta(BaseTransaction.Meta):
        unique_together = ('user', 'keyword')


class PostingTemplate(BasePosting):
    transaction = models.ForeignKey(
        'TransactionTemplate',
        on_delete=models.CASCADE,
    )
