from datetime import datetime
from decimal import Decimal

import pytest
import pytz
from freezegun import freeze_time

from beanbot.db import DB
from beanbot.models import Action, Event, Posting, Transaction, UserConfig


@pytest.fixture()
def sample_db():
    db = DB(
        user_data=dict(
            config=UserConfig(
                timezone='America/Lima',
                currencies=['USD', 'EUR'],
                credit_accounts=['Cash', 'Other'],
            ),
            next_ids=dict(transaction=2, posting=2),
        ),
    )
    tx = Transaction(1, datetime.now(), '', postings=[Posting(1, '', '', Decimal('0.00'), 'EUR')])
    db.transactions.append(tx)
    db.update_message_index(1, tx, tx.postings[0])
    return db


@freeze_time()
class TestDB:
    def test_new_transaction_message(self, sample_db: DB):
        tx, posting = sample_db.process_event(
            Event(
                action=Action.NEW,
                payload=dict(
                    info="test",
                    amount=Decimal('12.00'),
                ),
            )
        )

        assert len(sample_db.transactions) == 2
        assert tx == Transaction(
            id=2,
            date=datetime.now(pytz.timezone(sample_db.config.timezone)),
            info='',
            postings=[Posting(2, 'test', 'Cash', Decimal('12.00'), 'USD')],
        )

    def test_add_posting_message(self, sample_db: DB):
        tx, posting = sample_db.process_event(
            Event(
                action=Action.ADD,
                payload=dict(
                    info="test",
                    amount=Decimal('12.00'),
                ),
            )
        )

        assert len(sample_db.transactions) == 1
        assert len(tx.postings) == 2
        assert tx.postings[-1] == Posting(2, 'test', 'Cash', Decimal('12.00'), 'USD')

    def test_set_transaction_info_message(self, sample_db: DB):
        sample_db.process_event(
            Event(
                action=Action.SET_INFO,
                payload='New info',
            )
        )

        assert sample_db.transactions[-1].info == 'New info'

    def test_fix_amount_message(self, sample_db: DB):
        sample_db.process_event(
            Event(
                action=Action.FIX_AMOUNT,
                payload=Decimal(3.00),
            )
        )

        assert sample_db.transactions[-1].postings[-1].amount == Decimal(3.00)

        sample_db.process_event(
            Event(
                action=Action.FIX_AMOUNT,
                payload=Decimal(-2.00),
            )
        )

        assert sample_db.transactions[-1].postings[-1].amount == Decimal(1.00)

    def test_set_currency(self, sample_db: DB):
        sample_db.process_event(
            Event(
                action=Action.SET_CURRENCY,
                payload=0,
                message_id=1,
            )
        )

        assert sample_db.transactions[-1].postings[-1].currency == 'USD'

        sample_db.process_event(
            Event(
                action=Action.SET_CURRENCY,
                payload=1,
                message_id=1,
            )
        )

        assert sample_db.transactions[-1].postings[-1].currency == 'EUR'

    def test_set_credit_account(self, sample_db: DB):
        sample_db.process_event(
            Event(
                action=Action.SET_CREDIT_ACCOUNT,
                payload=1,
                message_id=1,
            )
        )

        assert sample_db.transactions[-1].postings[-1].credit_account == 'Other'

        sample_db.process_event(
            Event(
                action=Action.SET_CREDIT_ACCOUNT,
                payload=0,
                message_id=1,
            )
        )

        assert sample_db.transactions[-1].postings[-1].credit_account == 'Cash'

    def test_delete(self, sample_db: DB):
        assert len(sample_db.transactions) == 1

        sample_db.process_event(
            Event(
                action=Action.DELETE,
                payload=None,
                message_id=1,
            )
        )

        assert len(sample_db.transactions) == 0
