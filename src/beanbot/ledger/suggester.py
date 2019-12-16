from .models import (
    Account, Payee, Transaction, TransactionTemplate
)


class Clerk:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.archive = Transaction.objects.filter(user_id=user_id)
        self.templates = TransactionTemplate.objects.filter(user_id=user_id)
        self.accounts = Account.objects.filter(user_id=user_id)
        self.payee = Payee.objects.filter(user_id=user_id)

    def suggest_transaction(self, narration: str) -> Transaction:
        if (template := self._search_templates(narration)) is not None:
            return self._build_from_template(template)

        if (old_transaction := self._search_archive(narration)) is not None:
            return self._build_from_transaction(old_transaction, narration)

        return self._build_default_transaction(narration)

    def _search_templates(self, keyword):
        return self.templates.filter(keyword__iexact=keyword).first()

    def _search_archive(self, narration):
        return (
            self.archive
                .filter(narration__icontains=narration)
                .order_by('-created_at')
                .first()
        )

    def _build_from_template(self, template):
        return Transaction(template)

    def _build_from_transaction(self, old_transaction, narration):
        transaction = Transaction(old_transaction)
        transaction.narration = narration
        return transaction

    def _build_default_transaction(self, narration):
        account = self.accounts.filter(default=True).first()
        payee = self.accounts.filter(default=True).first()
        return Transaction(
            payee=payee,
            narration=narration,
            user_id=self.user_id,
        )
