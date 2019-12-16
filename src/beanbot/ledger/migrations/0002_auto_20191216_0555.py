# Generated by Django 3.0 on 2019-12-16 05:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ledger', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', related_query_name='account', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='payee',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payees', related_query_name='payee', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='posting',
            name='transaction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postings', related_query_name='posting', to='ledger.Transaction'),
        ),
        migrations.AlterField(
            model_name='postingtemplate',
            name='transaction',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postings', related_query_name='posting', to='ledger.TransactionTemplate'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', related_query_name='transaction', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='transactiontemplate',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='templates', related_query_name='template', to=settings.AUTH_USER_MODEL),
        ),
    ]
