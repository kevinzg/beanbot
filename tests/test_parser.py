from decimal import Decimal

import pytest
from freezegun import freeze_time

from beanbot.errors import UserError
from beanbot.models import Action, Event
from beanbot.parser import parse_keyboard_data, parse_message


invalid_messages = [
    'No money',
    'No currency 12.0 USD',
    '3.0',
    '+ no money' '+12 stuff',
    '-12 items',
    '#  ',
]


@freeze_time()
class TestParseEvent:
    def test_parse_set_info(self):
        assert parse_message('#New Info') == Event(Action.SET_INFO, 'New Info')
        assert parse_message('# New Info ') == Event(Action.SET_INFO, 'New Info')

    def test_parse_fix_amount(self):
        assert parse_message('+12.0') == Event(
            Action.FIX_AMOUNT,
            Decimal('12.0'),
        )
        assert parse_message('-0.30') == Event(
            Action.FIX_AMOUNT,
            Decimal('-0.30'),
        )
        assert parse_message('+.3') == Event(
            Action.FIX_AMOUNT,
            Decimal('0.3'),
        )

    def test_parse_new(self):
        assert parse_message('Something 12.0') == Event(
            Action.NEW,
            dict(
                info='Something',
                amount=Decimal('12.0'),
            ),
        )
        assert parse_message('Something more   -12.0') == Event(
            Action.NEW,
            dict(
                info='Something more',
                amount=Decimal('-12.0'),
            ),
        )
        assert parse_message('And more stuff .3') == Event(
            Action.NEW,
            dict(
                info='And more stuff',
                amount=Decimal('0.3'),
            ),
        )

    def test_parse_add(self):
        assert parse_message('+Add this 12.0') == Event(
            Action.ADD,
            dict(
                info='Add this',
                amount=Decimal('12.0'),
            ),
        )
        assert parse_message('+ And this   -3.0') == Event(
            Action.ADD,
            dict(
                info='And this',
                amount=Decimal('-3.0'),
            ),
        )

    def test_invalid_messages(self):
        for message in invalid_messages:
            with pytest.raises(UserError):
                parse_message(message)


@freeze_time()
class TestParseKeyboardData:
    def test_parse_set_currency(self):
        assert parse_keyboard_data('cur_0') == Event(Action.SET_CURRENCY, 0)
        assert parse_keyboard_data('cur_20') == Event(Action.SET_CURRENCY, 20)

    def test_parse_set_credit_account(self):
        assert parse_keyboard_data('acc_0') == Event(Action.SET_CREDIT_ACCOUNT, 0)
        assert parse_keyboard_data('acc_10') == Event(Action.SET_CREDIT_ACCOUNT, 10)

    def test_parse_delete(self):
        assert parse_keyboard_data('delete') == Event(Action.DELETE, None)

    def test_invalid_data(self):
        invalid_data = ['asd_123', '123', 'not_a_number']
        for data in invalid_data:
            with pytest.raises(ValueError):
                parse_keyboard_data(data)
