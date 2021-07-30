from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any, List, Optional

import pytz


# Models


@dataclass
class UserConfig:
    timezone: str = 'UTC'
    currencies: List[str] = field(default_factory=lambda: ['USD', 'EUR'])
    credit_accounts: List[str] = field(default_factory=lambda: ['Cash', 'CC', 'Other'])


@dataclass
class Posting:
    id: Optional[int]
    debit_account: str  # i.e. money is going into this account, usually an Expense
    credit_account: str  # i.e. money is going out of this account, usually an Asset
    amount: Decimal
    currency: str


@dataclass
class Transaction:
    id: Optional[int]
    date: datetime
    info: str
    postings: List[Posting] = field(default_factory=list)


class Action(Enum):
    NEW = auto()  # new transaction
    ADD = auto()  # add posting to last transaction
    SET_INFO = auto()  # Set last transaction info
    FIX_AMOUNT = auto()  # Increase/decrease last posting amount
    SET_CURRENCY = auto()  # Set currency of given posting
    SET_CREDIT_ACCOUNT = auto()  # Set credict account of given posting
    DELETE = auto()  # Delete posting or transaction
    COMMIT = auto()  # Commit transaction, don't allow modifications


@dataclass
class Event:
    """
    payload type depends on the action:
    - new: dict with info and amount
    - add: same as new
    - set_info: string with new info
    - fix_amount: Decimal with the increase amount
    - set_currency: index of currency in config
    - set_credit_account: index of account in config
    - delete: None
    """

    action: Action
    payload: Any
    date: datetime = field(default_factory=lambda: datetime.now(tz=pytz.utc))
    message_id: Optional[int] = None
