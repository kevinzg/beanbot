import textwrap
from decimal import Decimal

from beanbot.formatter import format_transaction
from beanbot.models import Posting, Transaction


class TestFormatTransaction:
    def test_format_simple_transaction(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
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
        `  10.00 USD `_Food_
        `=======`
        `- 10.00 USD `Cash
        """
            ).strip()
        )

    def test_format_simple_transaction_with_empty_info(self):
        tx = Transaction(
            id=1,
            date=None,
            info='',
            postings=[
                Posting(
                    id=1,
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
        `  10.00 USD `_Food_
        `=======`
        `- 10.00 USD `Cash
        """
            ).strip()
        )

    def test_format_transaction_two_postings(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=2,
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
        `  10.00 USD `_Food_
        `   2.00 USD `_Candy_
        `=======`
        `- 12.00 USD `Cash
        """
            ).strip()
        )

    def test_format_transaction_different_credit_account(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=2,
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
        `  10.00 USD `_Food_
        `   2.00 USD `_Candy_
        `=======`
        `- 10.00 USD `Cash
        `-  2.00 USD `CC
        """
            ).strip()
        )

    def test_format_transaction_default_currency(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=2,
                    debit_account='Candy',
                    credit_account='CC',
                    amount=Decimal(2),
                    currency='USD',
                ),
            ],
        )

        assert (
            format_transaction(tx, default_currency='USD')
            == textwrap.dedent(
                """
        Test
        `  10.00 `_Food_
        `   2.00 `_Candy_
        `=======`
        `- 10.00 `Cash
        `-  2.00 `CC
        """
            ).strip()
        )

    def test_format_transaction_different_credit_accounts_and_currency(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=2,
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
        `  10.00 USD `_Food_
        `   2.00 EUR `_Candy_
        `=======`
        `- 10.00 USD `Cash
        `-  2.00 EUR `CC
        """
            ).strip()
        )

    def test_format_transaction_postings_different_currency(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=2,
                    debit_account='Candy',
                    credit_account='Cash',
                    amount=Decimal(2),
                    currency='EUR',
                ),
            ],
        )

        formatted = textwrap.dedent(
            """
        Test
        `  10.00 USD `_Food_
        `   2.00 EUR `_Candy_
        `=======`
        `- 10.00 USD `Cash
        `-  2.00 EUR `
        """
        ).strip()

        assert format_transaction(tx) == formatted
        assert format_transaction(tx, default_currency='USD') == formatted

    def test_format_transaction_postings_credit_accounts_with_different_currency(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food',
                    credit_account='Cash',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=2,
                    debit_account='Candy',
                    credit_account='Cash',
                    amount=Decimal(2),
                    currency='EUR',
                ),
                Posting(
                    id=3,
                    debit_account='Books',
                    credit_account='Bank',
                    amount=Decimal(10),
                    currency='USD',
                ),
                Posting(
                    id=4,
                    debit_account='Cookies',
                    credit_account='Bank',
                    amount=Decimal(2),
                    currency='EUR',
                ),
            ],
        )

        formatted = textwrap.dedent(
            """
        Test
        `  10.00 USD `_Food_
        `   2.00 EUR `_Candy_
        `  10.00 USD `_Books_
        `   2.00 EUR `_Cookies_
        `=======`
        `- 10.00 USD `Cash
        `-  2.00 EUR `
        `- 10.00 USD `Bank
        `-  2.00 EUR `
        """
        ).strip()

        assert format_transaction(tx) == formatted
        assert format_transaction(tx, default_currency='USD') == formatted

    def test_escape_markdown(self):
        tx = Transaction(
            id=1,
            date=None,
            info='Test . _ * `',
            postings=[
                Posting(
                    id=1,
                    debit_account='Food.',
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
        Test \\. \\_ \\* \\`
        `  10.00 USD `_Food\\._
        `=======`
        `- 10.00 USD `Cash
        """
            ).strip()
        )
