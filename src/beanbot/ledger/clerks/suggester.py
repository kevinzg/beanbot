from beanbot.ledger.models import Posting

from .base import BaseClerk


class Suggester(BaseClerk):
    """Suggest transaction and accounts values based on a given narration"""

    def suggest_transaction(self, narration: str) -> dict:
        if (template := self._search_templates(narration)) is not None:
            return self._build_from_template(template)

        if (old_transaction := self._search_archive(narration)) is not None:
            return self._build_from_template(old_transaction, narration)

        return self._build_default_transaction(narration)

    def _search_templates(self, keyword):
        return self.templates.filter(keyword__iexact=keyword).first()

    def _search_archive(self, narration):
        return (
            self.transactions
                .filter(narration__icontains=narration)
                .order_by('-created_at')
                .first()
        )

    def _build_from_template(self, template, narration=None):
        return self._build_dict(
            narration=narration or template.narration,
            postings=template.postings.all(),
            payee_id=template.payee_id,
        )

    def _build_default_transaction(self, narration):
        target_account = self.accounts.get(default='t')
        source_account = self.accounts.get(default='s')
        payee = self.payees.filter(default=True).first()
        postings = [
            Posting(account_id=target_account.id),
            Posting(account_id=source_account.id),
        ]
        return self._build_dict(
            narration=narration,
            postings=postings,
            payee_id=payee.id,
        )

    @staticmethod
    def _build_dict(narration, postings, payee_id=None):
        return {
            'narration': narration,
            'payee_id': payee_id,
            'flag': '!',
            'target_accounts': [(p.account_id, p.amount) for p in postings if p.is_target],
            'source_accounts': [(p.account_id, p.amount) for p in postings if p.is_source],
        }
