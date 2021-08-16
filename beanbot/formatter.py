from decimal import Decimal
from typing import Dict

from telegram.utils import helpers

from .models import Posting, Transaction


# Formatter


def format_transaction(tx: Transaction, default_currency=None) -> str:
    """Returns a string representation of a transaction suitable for displaying in Telegram."""

    def format_debit(p: Posting, width: int, display_currency: bool) -> str:
        return "`{amount:= {width}.2f} {currency}`_{info}_".format(
            width=width,
            amount=p.amount,
            info=escape_markdown(p.debit_account),
            currency=f'{escape_markdown(p.currency)} ' if display_currency else '',
        )

    def format_credit(
        info: str, accumulators: Dict[str, Decimal], width: int, display_currency: bool
    ):
        return '\n'.join(
            "`{amount:= {width}.2f} {currency}`{info}".format(
                width=width,
                amount=amount,
                info=escape_markdown(info) if i == 0 else '',
                currency=f'{escape_markdown(currency)} ' if display_currency else '',
            )
            for i, (currency, amount) in enumerate(accumulators.items())
        )

    credits = {}
    currencies = set()
    amount_width = 0

    for p in tx.postings:
        # To count how many currencies there is
        currencies.add(p.currency)

        # To sum the credit account total
        accumulator = credits.setdefault(p.credit_account, {})
        accumulator.setdefault(p.currency, Decimal(0))
        accumulator[p.currency] -= p.amount

        # To format the amounts
        amount_width = max(amount_width, len(f"{accumulator[p.currency]:.2f}"))

    amount_width += 1
    display_currency = (
        len(currencies) > 1 or default_currency is None or default_currency not in currencies
    )

    debits = '\n'.join(
        format_debit(p, width=amount_width, display_currency=display_currency)
        for p in tx.postings
    )
    credits = '\n'.join(
        format_credit(info, acc, width=amount_width, display_currency=display_currency)
        for info, acc in credits.items()
    )
    sep = f"`{'=' * (amount_width)}`"

    # fmt: off
    return (
        '{header}'
        '{debits}\n'
        '{sep}\n'
        '{credits}\n'
    ).format(
        header=f'{escape_markdown(tx.info)}\n' if tx.info else '',
        debits=debits,
        sep=sep,
        credits=credits,
    ).strip()
    # fmt: on


def escape_markdown(s: str) -> str:
    return helpers.escape_markdown(s, version=2)
