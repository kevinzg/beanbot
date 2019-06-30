#!/usr/bin/env python

import datetime
import decimal
import itertools
import logging
import os

import pytz
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup)
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)


# Token
TOKEN = os.environ.get('BOT_TOKEN')

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# Models
PREFILLED_FIELDS = ('payee', 'account_1', 'account_2')


def make_date(timezone):
    timezone = pytz.timezone(timezone)
    return datetime.datetime.now(tz=timezone).date()


def make_new_transaction(user_config, **kwargs):
    transaction = {
        'date': make_date(user_config['timezone']),
        'info': '',
        'payee': user_config['payee'][0],
        'flag': user_config['flag'],
        'currency': user_config['currency'],
        'account_1': user_config['account_1'][0],
        'amount': decimal.Decimal(0),
        'account_2': user_config['account_2'][0],
    }
    transaction.update(kwargs)
    return transaction


def parse_message_transaction(text, user_config):
    try:
        *info, amount = text.strip().split()

        return make_new_transaction(
            user_config,
            info=' '.join(info),
            amount=decimal.Decimal(amount),
        )
    except (ValueError, decimal.InvalidOperation) as ex:
        raise ValueError from ex


def set_transaction_field(transaction, field, value):
    transaction[field] = value.strip()


def commit_transaction(transaction, user_data):
    transaction_list = user_data.setdefault('transaction_list', [])
    transaction_list.append(transaction)
    del user_data['current_transaction']


# Utils
def get_field_name(field):
    return {
        'payee': 'Payee',
        'account_1': "Expense account",
        'account_2': "Asset account",
        'info': "Info",
    }[field]


def set_default_user_config(user_data):
    user_data['config'] = dict(
        currency='USD',
        timezone='UTC',
        flag='*',
        payee=['Store', 'Restaurant', 'Taxi'],
        account_1=['Expenses:Stuff', 'Expenses:Food',
                   'Expenses:Transportation'],
        account_2=['Assets:Cash', 'Assets:Bank'],
        favorites=None,
    )


def get_user_config(user_data):
    if 'config' not in user_data:
        set_default_user_config(user_data)
    return user_data['config']


class KeyboardFactory:
    @staticmethod
    def _make_inline_keyboard(labels, data, cols=2):
        button_kwargs = [dict(text=label, callback_data=datum)
                         for label, datum in zip(labels, data)]
        rows = len(data) // cols + len(data) % cols

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(**kwargs)
             for kwargs in itertools.islice(
                 button_kwargs, start * cols, start * cols + cols)]
            for start in range(rows)
        ])

    @staticmethod
    def make_generic_inline_keyboard(type_, labels, cols=2, back=True,
                                     back_data='go_back', back_label="« Back"):
        labels = list(labels)
        n = len(labels)
        data = [f'{type_}_{i}' for i in range(n)]

        if back:
            labels.append(back_label)
            data.append(back_data)

        return KeyboardFactory._make_inline_keyboard(labels, data, cols)

    @staticmethod
    def make_main_inline_keyboard():
        buttons = [
            ('Payee', 'payee'),
            ('Info', 'info'),
            ('Expense acct.', 'account_1'),
            ('Asset acct.', 'account_2'),
            ('Cancel', 'cancel'),
            ('Done', 'done'),
        ]

        return KeyboardFactory._make_inline_keyboard(
            [button[0] for button in buttons],
            [button[1] for button in buttons],
        )


def clear_inline_keyboard(update):
    update.callback_query.edit_message_reply_markup(
        InlineKeyboardMarkup([[]])
    )


def extract_index(data):
    idx = data.split('_')[-1]
    return int(idx)


# States
WAITING_TRANSACTION, SELECTING_FIELD, FILLING_DATA = range(3)


def format_transaction(transaction):
    header = ' - '.join(filter(None,
                               (transaction['payee'], transaction['info'])))
    return ('{date} {flag} {header}\n'
            '    {account_1}    {amount:.2f} {currency}\n'
            '    {account_2}').format(
                **transaction,
                header=header
            )


def send_transaction_and_keyboard(update, transaction, inline_keyboard=None,
                                  do_update=False):
    if inline_keyboard is None:
        inline_keyboard = KeyboardFactory.make_main_inline_keyboard()

    formatted_transaction = format_transaction(transaction)

    if do_update:
        update.callback_query.edit_message_text(formatted_transaction,
                                                reply_markup=inline_keyboard)
    else:
        update.message.reply_text(formatted_transaction,
                                  reply_markup=inline_keyboard)


def start(update, context):
    update.message.reply_text(
        "Hi! I'm BeanBot. Help will go here, but it hasn't been written yet.",
    )

    return WAITING_TRANSACTION


def register_transaction(update, context):
    user_config = get_user_config(context.user_data)
    message_text = update.message.text

    try:
        transaction = parse_message_transaction(message_text,
                                                user_config)
    except ValueError:
        update.message.reply_text("Seems like the amount is missing.")
        return WAITING_TRANSACTION
    except Exception as ex:
        update.message.reply_text("Sorry, I couldn't understand that.")
        logger.exception("Could not parse transaction", ex)
        return WAITING_TRANSACTION

    context.user_data['current_transaction'] = transaction

    send_transaction_and_keyboard(update, transaction)

    return SELECTING_FIELD


def selecting_field(update, context):
    button = update.callback_query.data
    current_transaction = context.user_data['current_transaction']
    user_config = get_user_config(context.user_data)

    if button == 'done':
        commit_transaction(current_transaction, context.user_data)
        clear_inline_keyboard(update)

        update.callback_query.answer('Saved!')

        return WAITING_TRANSACTION
    elif button == 'cancel':
        clear_inline_keyboard(update)
        update.callback_query.edit_message_text('Canceled transaction')

        del context.user_data['current_transaction']

        update.callback_query.answer('Canceled!')

        return WAITING_TRANSACTION

    context.user_data['field'] = button

    labels = []
    msg = 'Write a value'
    if button in PREFILLED_FIELDS:
        labels = user_config[button]
        msg = 'Select or write a value'

    keyboard = KeyboardFactory.make_generic_inline_keyboard(button, labels)

    send_transaction_and_keyboard(update, current_transaction,
                                  inline_keyboard=keyboard, do_update=True)

    update.callback_query.answer(msg)

    return FILLING_DATA


def filling_data_button(update, context):
    button_data = update.callback_query.data
    current_transaction = context.user_data['current_transaction']
    current_field = context.user_data['field']
    user_config = get_user_config(context.user_data)

    if button_data != 'go_back':
        try:
            index = extract_index(button_data)
            value = user_config[current_field][index]
        except Exception as ex:
            update.callback_query.answer("Sorry, I couldn't process that.")
            logger.exception(ex)
        else:
            set_transaction_field(current_transaction, current_field, value)
            update.callback_query.answer("Got it!")
    else:
        update.callback_query.answer()

    send_transaction_and_keyboard(update, current_transaction,
                                  do_update=True)

    del context.user_data['field']
    return SELECTING_FIELD


def filling_data_text(update, context):
    current_transaction = context.user_data['current_transaction']
    current_field = context.user_data['field']
    datum = update.message.text

    set_transaction_field(current_transaction, current_field, datum)

    send_transaction_and_keyboard(update, current_transaction)

    del context.user_data['field']
    return SELECTING_FIELD


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def fallback(update, context):
    update.message.reply_text("I got lost. Can try again?")
    return WAITING_TRANSACTION


def main():
    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text, register_transaction,
                                     pass_user_data=True)],
        states={
            WAITING_TRANSACTION: [MessageHandler(Filters.text,
                                                 register_transaction,
                                                 pass_user_data=True)],
            SELECTING_FIELD: [CallbackQueryHandler(selecting_field,
                                                   pass_user_data=True)],
            FILLING_DATA: [CallbackQueryHandler(filling_data_button,
                                                pass_user_data=True),
                           MessageHandler(Filters.text, filling_data_text,
                                          pass_user_data=True)],
        },
        fallbacks=[MessageHandler(Filters.text, fallback,
                                  pass_user_data=True)],
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
