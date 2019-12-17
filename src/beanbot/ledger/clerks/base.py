from beanbot.users.models import User


class BaseClerk:
    """Base class for clerks"""

    def __init__(self, user: User):
        self.user = user

    @property
    def transactions(self):
        return self.user.transactions

    @property
    def templates(self):
        return self.user.templates

    @property
    def accounts(self):
        return self.user.accounts

    @property
    def payees(self):
        return self.user.payees
