from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass
class Message:
    info: str
    amount: Decimal
    days_old: int = 0

    @classmethod
    def parse(cls, raw_message: str) -> Message:
        carets = cls._count_carets(raw_message)
        *info, amount = raw_message[carets:].strip().split()

        try:
            return cls(
                info=' '.join(info),
                amount=Decimal(amount),
                days_old=carets)
        except (ValueError, InvalidOperation) as ex:
            raise ValueError(f"Cannot parse message: {raw_message!r}") from ex

    @staticmethod
    def _count_carets(text):
        for i, c in enumerate(text):
            if c != '^':
                return i
        return 0
