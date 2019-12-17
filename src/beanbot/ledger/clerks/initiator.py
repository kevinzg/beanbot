from beanbot.ledger.constants import (DEFAULT_SOURCE_ACCOUNT,
                                      DEFAULT_TARGET_ACCOUNT, SOURCE, TARGET)

from .. import utils
from ..models import Account
from .base import BaseClerk


class Initiator(BaseClerk):
    """Opens accounts"""

    def open_account(self, name: str, **kwargs) -> Account:
        kwargs.setdefault('display_name', utils.get_last_account_fragment(name))

        return self.accounts.create(
            name=name,
            **kwargs,
        )

    def open_default_accounts(self):
        self.open_account(DEFAULT_SOURCE_ACCOUNT, default=SOURCE)
        self.open_account(DEFAULT_TARGET_ACCOUNT, default=TARGET)
