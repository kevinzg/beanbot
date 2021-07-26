from decimal import Decimal

import pytest
from freezegun import freeze_time

from beanbot.errors import UserError
from beanbot.models import Message
from beanbot.parser import parse_message


invalid_messages = [
    'No money',
    'No currency 12.0 USD',
    '3.0',
    '+ no money' '+12 stuff',
    '-12 items',
    '#  ',
]


@freeze_time()
class TestParseMessage:
    def test_parse_set_info(self):
        assert parse_message('#New Info') == Message('set_info', 'New Info')
        assert parse_message('# New Info ') == Message('set_info', 'New Info')

    def test_parse_fix_amount(self):
        assert parse_message('+12.0') == Message(
            'fix_amount',
            Decimal('12.0'),
        )
        assert parse_message('-0.30') == Message(
            'fix_amount',
            Decimal('-0.30'),
        )
        assert parse_message('+.3') == Message(
            'fix_amount',
            Decimal('0.3'),
        )

    def test_parse_new(self):
        assert parse_message('Something 12.0') == Message(
            'new',
            dict(
                info='Something',
                amount=Decimal('12.0'),
            ),
        )
        assert parse_message('Something more   -12.0') == Message(
            'new',
            dict(
                info='Something more',
                amount=Decimal('-12.0'),
            ),
        )
        assert parse_message('And more stuff .3') == Message(
            'new',
            dict(
                info='And more stuff',
                amount=Decimal('0.3'),
            ),
        )

    def test_parse_add(self):
        assert parse_message('+Add this 12.0') == Message(
            'add',
            dict(
                info='Add this',
                amount=Decimal('12.0'),
            ),
        )
        assert parse_message('+ And this   -3.0') == Message(
            'add',
            dict(
                info='And this',
                amount=Decimal('-3.0'),
            ),
        )

    def test_invalid_messages(self):
        for message in invalid_messages:
            with pytest.raises(UserError):
                parse_message(message)
