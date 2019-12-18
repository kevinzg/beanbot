from rest_framework import serializers

from beanbot.users.models import User

from .models import Account, Payee


class UserOwnedRelatedField(serializers.PrimaryKeyRelatedField):
    """Checks that the field is owned by the user given on the context"""

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.context['user']
        return queryset.filter(user=user).only('pk')

    def to_internal_value(self, data):
        return super().to_internal_value(data).pk


class BaseForm(serializers.Serializer):
    def __init__(self, data: dict, user: User):
        super().__init__(data=data, context={'user': user})


class RegisterTransactionForm(BaseForm):
    """Form to register a new transaction"""

    narration = serializers.CharField(allow_blank=True)
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    target_account_id = UserOwnedRelatedField(queryset=Account.objects)
    source_account_id = UserOwnedRelatedField(queryset=Account.objects)
    payee_id = UserOwnedRelatedField(queryset=Payee.objects, allow_null=True)
