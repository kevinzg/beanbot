from django.conf import settings

User = settings.AUTH_USER_MODEL


class BaseClerk:
    """Base class for clerks"""

    def __init__(self, user_id: int):
        self.user = User.objects.get(user_id=user_id)

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
