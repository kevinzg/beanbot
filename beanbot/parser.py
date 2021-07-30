from decimal import Decimal, InvalidOperation

from .errors import UserError
from .models import Action, Event


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
        return Event(Action.SET_INFO, info)

    if message.startswith('+') or message.startswith('-'):
        diff = None
        try:
            diff = Decimal(message)
        except (ValueError, InvalidOperation):
            pass
        if diff is not None:
            return Event(Action.FIX_AMOUNT, diff)

    if message.startswith('+'):
        message = message[1:]
        return Event(Action.ADD, inner_parse())

    return Event(Action.NEW, inner_parse())


def parse_keyboard_data(data: str) -> Event:
    if data == 'delete':
        return Event(Action.DELETE, None)
    elif data == 'commit':
        return Event(Action.COMMIT, None)

    key, index = data.rsplit('_', maxsplit=1)
    index = int(index)

    if key == 'cur':
        return Event(Action.SET_CURRENCY, index)
    elif key == 'acc':
        return Event(Action.SET_CREDIT_ACCOUNT, index)

    raise ValueError(f'Invalid key ${key}')
