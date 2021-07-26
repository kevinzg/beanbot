from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz

from .errors import UserError
from .models import Event, Posting, Transaction, UserConfig


# Database


class DB:
    def __init__(self, user_data: Dict[str, Any]):
        """Creates a database interface on top of `user_data`.

        `user_data` should be PTB's `context.user_data` but can be any dict.
        """
        self.transactions: List[Transaction] = user_data.setdefault('transactions', [])
        self.config: UserConfig = user_data.setdefault('config', UserConfig())

        self.last_event: Optional[datetime] = None

    @property
    def last_transaction(self):
        if self.transactions:
            return self.transactions[-1]
        raise UserError('There are no transactions')

    @property
    def last_posting(self):
        if self.last_transaction.postings:
            return self.last_transaction.postings[-1]
        raise UserError('There are no postings')


    def process_event(self, event: Event) -> Tuple[Transaction, Optional[Posting]]:
        # Convert `new` to `add` if the last event was received in the last 5 minutes
        if event.action == 'new':
            if self.last_event and (event.date - self.last_event) < timedelta(minutes=5):
                event.action = 'add'

        self.last_event = datetime.now(pytz.UTC)

        # Convert `add` to `new` if there are no previous transactions
        if event.action == 'add' and not self.transactions:
            event.action = 'new'

        tx = None
        posting = None

        # Creates the posting for `new` and `add`.
        def make_posting():
            return Posting(
                debit_account=event.payload['info'],
                credit_account=self.config.credit_accounts[0],
                amount=event.payload['amount'],
                currency=self.config.currencies[0],
            )

        # Handle event
        if event.action == 'new':
            posting = make_posting()
            tx = Transaction(
                date=event.date.astimezone(pytz.timezone(self.config.timezone)),
                info=event.payload['info'],
                postings=[posting],
            )
            self.transactions.append(tx)

        elif event.action == 'add':
            posting = make_posting()
            tx = self.last_transaction
            tx.postings.append(posting)

        elif event.action == 'set_info':
            tx = self.last_transaction
            tx.info = event.payload

        elif event.action == 'fix_amount':
            tx = self.last_transaction
            posting = self.last_posting
            posting.amount += event.payload

            tx = self.last_transaction
            posting = self.last_posting
        elif event.action == 'set_currency':
            posting.currency = self.config.currencies[event.payload]

        elif event.action == 'set_credit_account':
            tx = self.last_transaction
            posting = self.last_posting
            posting.credit_account = self.config.credit_accounts[event.payload]

        return tx, posting
