from functools import wraps

from .exceptions import Rejection


def split_account_name(name: str):
    return name.split(':')


def get_last_account_fragment(account_name: str):
    return split_account_name(account_name)[-1]


def validate_data(validator_class):
    def decorator(method):
        @wraps(method)
        def validate_and_submit(self, data: dict):
            validator = validator_class(data=data, user=self.user)
            if validator.is_valid():
                return method(self, validator.validated_data)
            raise Rejection(reasons=validator.errors)
        return validate_and_submit
    return decorator
