import textwrap
from decimal import Decimal

from beanbot.formatter import format_transaction
from beanbot.models import Posting, Transaction


class TestFormatTransaction:
    def test_format_simple_transaction(self):
        tx = Transaction(
            date=None,
            info='Test',
            postings=[
                Posting(
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                )
            ],
        )

        assert (
            format_transaction(tx)
            == textwrap.dedent(
                """
        Test
        `  10.00` __Food__
        """
            ).strip()
        )

    def test_format_transaction_two_postings(self):
        tx = Transaction(
            date=None,
            info='Test',
            postings=[
                Posting(
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    debit_account='Candy',
                    credit_account='Cash',
                    amount=Decimal(2),
                    currency='USD',
                ),
            ],
        )

        assert (
            format_transaction(tx)
            == textwrap.dedent(
                """
        Test
        `  10.00` __Food__
        `   2.00` __Candy__
        `=======`
        `- 12.00` Cash
        """
            ).strip()
        )

    def test_format_transaction_different_credit_account(self):
        tx = Transaction(
            date=None,
            info='Test',
            postings=[
                Posting(
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    debit_account='Candy',
                    credit_account='CC',
                    amount=Decimal(2),
                    currency='USD',
                ),
            ],
        )

        assert (
            format_transaction(tx)
            == textwrap.dedent(
                """
        Test
        `  10.00` __Food__
        `   2.00` __Candy__
        `=======`
        `- 10.00` Cash
        `-  2.00` CC
        """
            ).strip()
        )

    def test_format_transaction_different_credit_accounts_and_currency(self):
        tx = Transaction(
            date=None,
            info='Test',
            postings=[
                Posting(
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    debit_account='Candy',
                    credit_account='CC',
                    amount=Decimal(2),
                    currency='EUR',
                ),
            ],
        )

        assert (
            format_transaction(tx)
            == textwrap.dedent(
                """
        Test
        `  10.00 USD` __Food__
        `   2.00 EUR` __Candy__
        `=======`
        `- 10.00 USD` Cash
        `-  2.00 EUR` CC
        """
            ).strip()
        )

    def test_format_transaction_postings_different_currency(self):
        tx = Transaction(
            date=None,
            info='Test',
            postings=[
                Posting(
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    debit_account='Candy',
                    credit_account='Cash',
                    amount=Decimal(2),
                    currency='EUR',
                ),
            ],
        )

        assert (
            format_transaction(tx)
            == textwrap.dedent(
                """
        Test
        `  10.00 USD` __Food__
        `   2.00 EUR` __Candy__
        `=======`
        `- 10.00 USD` Cash
        `-  2.00 EUR`
        """
            ).strip()
        )
