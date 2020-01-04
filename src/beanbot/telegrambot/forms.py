from django import forms

from beanbot.ledger.models import Account, Payee


class TransactionForm(forms.Form):
    date = forms.DateField()
    narration = forms.CharField()
    amount = forms.DecimalField()
    payee = forms.ModelChoiceField(queryset=Payee.objects)
    source_account = forms.ModelChoiceField(queryset=Account.objects)
    target_account = forms.ModelChoiceField(queryset=Account.objects)
