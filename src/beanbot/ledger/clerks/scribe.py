from .base import BaseClerk


class Scribe(BaseClerk):
    """Writes a journal with the user's transactions"""

    def write_journal(self) -> str:
        transactions = []
        for tx in self.transactions.all():
            transactions.append(
                f"{tx.date} {tx.flag} {tx.payee!r} {tx.narration!r}"
            )
        return "\n".join(transactions)
