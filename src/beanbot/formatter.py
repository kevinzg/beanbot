from decimal import Decimal
from typing import Dict

from .models import Posting, Transaction


# Formatter


def format_transaction(tx: Transaction) -> str:
    """Returns a string representation of a transaction suitable for displaying in Telegram."""

    def format_debit(p: Posting, width: int, display_currency: bool) -> str:
        return "`{amount:= {width}.2f}{currency}` __{info}__".format(
            width=width,
            amount=p.amount,
            info=p.debit_account,
            currency=f' {p.currency}' if display_currency else '',
        )

    def format_credit(
        info: str, accumulators: Dict[str, Decimal], width: int, display_currency: bool
    ):
        return '\n'.join(
            "`{amount:= {width}.2f}{currency}` {info}".format(
                width=width,
                amount=amount,
                info=info if i == 0 else '',
                currency=f' {currency}' if display_currency else '',
            ).strip()
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

    display_currency = len(currencies) > 1
    debits = '\n'.join(
        format_debit(p, width=amount_width, display_currency=display_currency)
        for p in tx.postings
    )
    display_credits = len(tx.postings) > 1
    credits = (
        '\n'.join(
            format_credit(info, acc, width=amount_width, display_currency=display_currency)
            for info, acc in credits.items()
        )
        if len(tx.postings) > 1
        else ''
    )
    sep = f"`{'=' * (amount_width)}`" if display_credits else ''

    # fmt: off
    return (
        '{header}\n'
        '{debits}\n'
        '{sep}\n'
        '{credits}\n'
    ).format(
        header=tx.info,
        debits=debits,
        sep=sep,
        credits=credits,
    ).strip()
    # fmt: on
