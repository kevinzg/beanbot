from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account, Payee, Transaction, TransactionTemplate

admin.site.register(Account)
admin.site.register(Payee)
admin.site.register(Transaction)
admin.site.register(TransactionTemplate)
