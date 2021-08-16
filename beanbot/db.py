from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz

from .errors import UserError
from .models import Action, Event, Posting, Transaction, UserConfig


# Database


class DB:
    def __init__(self, user_data: Dict[str, Any]):
        """Creates a database interface on top of `user_data`.

        `user_data` should be PTB's `context.user_data` but can be any dict.
        """
        self.transactions: List[Transaction] = user_data.setdefault('transactions', [])
        self.config: UserConfig = user_data.setdefault('config', UserConfig())

        self.next_ids = user_data.setdefault('next_ids', dict(transaction=1, posting=1))
        self.message_id_index: Dict[int, Tuple[int, Optional[int]]] = user_data.setdefault(
            'message_id_index', {}
        )
        self.vars = user_data.setdefault('vars', {})

    @property
    def last_entries(self) -> Tuple[Transaction, Posting]:
        if self.transactions:
            tx = self.transactions[-1]
            return tx, tx.postings[-1]
        raise UserError('There are no transactions')

    def get_entries_by_message_id(self, message_id: int) -> Tuple[Transaction, Optional[Posting]]:
        index = self.message_id_index.get(message_id)
        if index is None:
            raise UserError(f'No transaction for message {message_id}')

        # TODO: Could be binary search
        tx = next(filter(lambda v: v.id == index[0], self.transactions), None)
        if tx is None:
            raise UserError(f'No transaction for message {message_id}')

        posting = index[1] and next(filter(lambda v: v.id == index[1], tx.postings), None)
        return tx, posting

    def process_event(self, event: Event) -> Tuple[Transaction, Optional[Posting]]:
        # Convert `new` to `add` if the last event was received in the last 5 minutes
        if event.action == Action.NEW:
            if self.last_event and (event.date - self.last_event) < timedelta(minutes=5):
                event.action = Action.ADD

        self.last_event = event.date

        # Convert `add` to `new` if there are no previous transactions
        if event.action == Action.ADD and not self.transactions:
            event.action = Action.NEW

        # Helper functions
        def create_new_transaction() -> Transaction:
            tx = Transaction(
                id=self.next_ids['transaction'],
                date=event.date.astimezone(self.config.tzinfo),
                info='',
                postings=[],
            )
            self.next_ids['transaction'] += 1
            self.transactions.append(tx)
            return tx

        def create_new_posting(tx: Transaction) -> Posting:
            posting = Posting(
                id=self.next_ids['posting'],
                debit_account=event.payload['info'],
                credit_account=self.config.credit_accounts[0],
                amount=event.payload['amount'],
                currency=self.config.currencies[0],
            )
            self.next_ids['posting'] += 1
            tx.postings.append(posting)
            return posting

        tx, posting = None, None

        # Handle events
        if event.action == Action.NEW:
            tx = create_new_transaction()
            posting = create_new_posting(tx)

        elif event.action == Action.ADD:
            tx, _ = self.last_entries
            posting = create_new_posting(tx)

        elif event.action == Action.SET_INFO:
            tx, _ = self.last_entries
            tx.info = event.payload

        elif event.action == Action.FIX_AMOUNT:
            tx, posting = self.last_entries
            posting.amount += event.payload

        elif event.action == Action.SET_CURRENCY:
            tx, posting = self.get_entries_by_message_id(event.message_id)
            posting.currency = self.config.currencies[event.payload]

        elif event.action == Action.SET_CREDIT_ACCOUNT:
            tx, posting = self.get_entries_by_message_id(event.message_id)
            posting.credit_account = self.config.credit_accounts[event.payload]

        elif event.action == Action.DELETE:
            tx, posting = self.get_entries_by_message_id(event.message_id)
            if posting is None:
                raise UserError(f'Not posting for message {event.message_id}')
            tx.postings.remove(posting)
            if not tx.postings:
                # TODO: Clear the index
                self.transactions.remove(tx)

        elif event.action == Action.COMMIT:
            self.last_event = None

        return tx, posting

    def clear(self):
        self.transactions.clear()
        self.message_id_index.clear()
        self.last_event = None

    def update_message_index(self, message_id: int, tx: Transaction, posting: Posting):
        assert message_id is not None
        assert tx.id is not None
        self.message_id_index[message_id] = (tx.id, posting and posting.id)

    @property
    def last_event(self) -> Optional[datetime]:
        return self.vars.get('last_event')

    @last_event.setter
    def last_event(self, value: datetime):
        self.vars['last_event'] = value
