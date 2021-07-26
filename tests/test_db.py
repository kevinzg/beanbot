from datetime import datetime
from decimal import Decimal

import pytest
import pytz
from freezegun import freeze_time

from beanbot.db import DB
from beanbot.models import Message, Posting, Transaction, UserConfig


@pytest.fixture()
def sample_db():
    db = DB(
        user_data=dict(
            config=UserConfig(
                timezone='America/Lima',
                currencies=['USD', 'EUR'],
                credit_accounts=['Cash', 'Other'],
            )
        ),
    )
    db.transactions.append(
        Transaction(datetime.now(), '', postings=[Posting('', '', Decimal('0.00'), 'EUR')])
    )
    return db


@freeze_time()
class TestDB:
    def test_new_transaction_message(self, sample_db: DB):
        sample_db.process_message(
            Message(
                action='new',
                payload=dict(
                    info="test",
                    amount=Decimal('12.00'),
                ),
            )
        )

        assert len(sample_db.transactions) == 2
        assert sample_db.last_transaction == Transaction(
            date=datetime.now(pytz.timezone(sample_db.config.timezone)),
            info='test',
            postings=[Posting('test', 'Cash', Decimal('12.00'), 'USD')],
        )

    def test_add_posting_message(self, sample_db: DB):
        sample_db.process_message(
            Message(
                action='add',
                payload=dict(
                    info="test",
                    amount=Decimal('12.00'),
                ),
            )
        )

        assert len(sample_db.transactions) == 1
        assert len(sample_db.last_transaction.postings) == 2
        assert sample_db.last_posting == Posting('test', 'Cash', Decimal('12.00'), 'USD')

    def test_set_transaction_info_message(self, sample_db: DB):
        sample_db.process_message(
            Message(
                action='set_info',
                payload='New info',
            )
        )

        assert sample_db.last_transaction.info == 'New info'

    def test_fix_amount_message(self, sample_db: DB):
        sample_db.process_message(
            Message(
                action='fix_amount',
                payload=Decimal(3.00),
            )
        )

        assert sample_db.last_posting.amount == Decimal(3.00)

        sample_db.process_message(
            Message(
                action='fix_amount',
                payload=Decimal(-2.00),
            )
        )

        assert sample_db.last_posting.amount == Decimal(1.00)

    def test_set_currency(self, sample_db: DB):
        sample_db.process_message(
            Message(
                action='set_currency',
                payload=0,
            )
        )

        assert sample_db.last_posting.currency == 'USD'

        sample_db.process_message(
            Message(
                action='set_currency',
                payload=1,
            )
        )

        assert sample_db.last_posting.currency == 'EUR'

    def test_set_credit_account(self, sample_db: DB):
        sample_db.process_message(
            Message(
                action='set_credit_account',
                payload=1,
            )
        )

        assert sample_db.last_posting.credit_account == 'Other'

        sample_db.process_message(
            Message(
                action='set_credit_account',
                payload=0,
            )
        )

        assert sample_db.last_posting.credit_account == 'Cash'
