from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz

from .errors import UserError
from .models import Message, Posting, Transaction, UserConfig


# Database


class DB:
    def __init__(self, user_data: Dict[str, Any]):
        """Creates a database interface on top of `user_data`.

        `user_data` should be PTB's `context.user_data` but can be any dict.
        """
        self.transactions: List[Transaction] = user_data.setdefault('transactions', [])
        self.config: UserConfig = user_data.setdefault('config', UserConfig())
        self.last_message: Optional[datetime.datetime] = None

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

    def process_message(self, message: Message) -> Tuple[Transaction, Optional[Posting]]:
        # Convert `new` to `add` if the last message was received in the last 5 minutes
        if message.action == 'new':
            if self.last_message is not None and (
                message.date - self.last_message
            ) < datetime.timedelta(minutes=5):
                message.action = 'add'

        self.last_message = datetime.now(pytz.UTC)

        # Convert `add` to `new` if there are no previous transactions
        if message.action == 'add' and not self.transactions:
            message.action = 'new'

        tx = None
        posting = None

        # Create posting for new/add
        if message.action in ['new', 'add']:
            posting = Posting(
                debit_account=message.payload['info'],
                credit_account=self.config.credit_accounts[0],
                amount=message.payload['amount'],
                currency=self.config.currencies[0],
            )

        # Handle message
        if message.action == 'new':
            tx = Transaction(
                date=message.date.astimezone(pytz.timezone(self.config.timezone)),
                info=message.payload['info'],
                postings=[posting],
            )
            self.transactions.append(tx)

        elif message.action == 'add':
            tx = self.last_transaction
            tx.postings.append(posting)

        elif message.action == 'set_info':
            tx = self.last_transaction
            tx.info = message.payload

        elif message.action == 'fix_amount':
            tx = self.last_transaction
            posting = self.last_posting
            posting.amount += message.payload

        return tx, posting
