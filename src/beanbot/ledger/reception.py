from beanbot.users.models import User

from .clerks import Registrar
from .models import Transaction
from .utils import validate_data
from .validators import RegisterTransactionValidator


class ReceptionDesk:
    def __init__(self, user: User):
        self.user = user

    @validate_data(RegisterTransactionValidator)
    def submit_transaction(self, data: dict) -> Transaction:
        return Registrar(self.user).register_transaction(**data)
