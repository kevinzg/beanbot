from decimal import Decimal, InvalidOperation

from .errors import UserError
from .models import Event


# Parser


def parse_message(message: str) -> Event:
    """Transform a user message into an event that can be handled by the database."""
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
        return Event('set_info', info)

    if message.startswith('+') or message.startswith('-'):
        diff = None
        try:
            diff = Decimal(message)
        except (ValueError, InvalidOperation):
            pass
        if diff is not None:
            return Event('fix_amount', diff)

    if message.startswith('+'):
        message = message[1:]
        return Event('add', inner_parse())

    return Event('new', inner_parse())


def parse_keyboard_data(data: str) -> Event:
    key, index = data.rsplit('_', maxsplit=1)
    index = int(index)

    if key == 'cur':
        return Event('set_currency', index)
    elif key == 'acc':
        return Event('set_credit_account', index)

    raise ValueError(f'Invalid key ${key}')
