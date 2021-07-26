from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, List

import pytz


# Models


@dataclass
class UserConfig:
    timezone: str = 'UTC'
    currencies: List[str] = field(default_factory=lambda: ['USD', 'EUR'])
    credit_accounts: List[str] = field(default_factory=lambda: ['Cash', 'CC', 'Other'])


@dataclass
class Posting:
    debit_account: str  # i.e. money is going into this account, usually an Expense
    credit_account: str  # i.e. money is going out of this account, usually an Asset
    amount: Decimal
    currency: str


@dataclass
class Transaction:
    date: datetime
    info: str
    postings: List[Posting] = field(default_factory=list)


@dataclass
class Message:
    """
    action can be:
    - new: New transaction
    - add: Add posting to last transaction
    - set_info: Overwrite last transaction info
    - fix_amount: Increment last posting amount
    - set_currency: Set currency of last posting
    - set_credit_account: Set credit account of last posting

    payload type depends on the action:
    - new: dict with info and amount
    - add: same as new
    - set_info: string with new info
    - fix_amount: Decimal with the increase amount
    - set_currency: index of currency in config
    - set_credit_account: index of account in config
    """

    action: str  # new, add, set_info or fix_amount
    payload: Any
    date: datetime = field(default_factory=lambda: datetime.now(tz=pytz.utc))
