from datetime import date as Date
from decimal import Decimal

from beanbot.ledger.models import Transaction

from .base import BaseClerk


class Registrar(BaseClerk):
    """Registers transactions"""

    def register_transaction(
            self,
            narration: str,
            date: Date,
            amount: Decimal,
            target_account_id: int,
            source_account_id: int,
            payee_id: int = None,
    ) -> Transaction:
        transaction = self.transactions.create(
            narration=narration,
            date=date,
            payee_id=payee_id,
            flag='*',
        )
        transaction.postings.create(
            account_id=target_account_id,
            amount=amount,
            explicit=True,
            transaction=transaction,
        )
        transaction.postings.create(
            account_id=source_account_id,
            amount=amount * -1,
            explicit=False,
            transaction=transaction,
        )

        return transaction
