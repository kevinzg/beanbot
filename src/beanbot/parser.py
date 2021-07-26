from decimal import Decimal, InvalidOperation

from .errors import UserError
from .models import Message


# Parser


def parse_message(message: str) -> Message:
    """Transform a user message into a message that can be handled by the database."""
    message = message.strip()

    def inner_parse():
        try:
            *info, amount = message.split()
            info = ' '.join(info).strip()
            if not info:
                raise UserError("Info can't be empty")
            return dict(
                info=info,
                amount=Decimal(amount),
            )
        except (ValueError, InvalidOperation) as ex:
            raise UserError from ex

    if message.startswith('#'):
        info = message[1:].strip()
        if not info:
            raise UserError("Info can't be empty")
        return Message('set_info', info)

    if message.startswith('+') or message.startswith('-'):
        diff = None
        try:
            diff = Decimal(message)
        except (ValueError, InvalidOperation):
            pass
        if diff is not None:
            return Message('fix_amount', diff)

    if message.startswith('+'):
        message = message[1:]
        return Message('add', inner_parse())

    return Message('new', inner_parse())
