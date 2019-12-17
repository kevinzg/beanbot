from ..models import Payee
from .base import BaseClerk


class ContactKeeper(BaseClerk):
    """Adds payees"""

    def add_payee(self, name) -> Payee:
        return self.payees.create(
            name=name,
        )
