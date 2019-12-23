#!/usr/bin/env python

import datetime
import itertools
import logging
import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pytz
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup)
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          PicklePersistence, Updater)


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
        'amount': Decimal(0),
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
            amount=Decimal(amount),
        )
    except (ValueError, InvalidOperation) as ex:
        raise ValueError from ex


def format_transaction(transaction, beancount=False):
    if beancount:
        sep = ' '
        fmt = lambda x: '"{}"'.format(x)  # noqa: E731
    else:
        sep = ' - '
        fmt = lambda x: x  # noqa: E731

    header = sep.join(
        fmt(x)
        for x in filter(None, (transaction['payee'], transaction['info']))
    )

    return ('{date} {flag} {header}\n'
            '    {account_1}    {amount:.2f} {currency}\n'
            '    {account_2}').format(
                **transaction,
                header=header
            )


def set_transaction_field(transaction, field, value):
    transaction[field] = value.strip()


def get_transaction_list(user_data):
    return user_data.setdefault('transaction_list', [])


def commit_transaction(transaction, user_data):
    transaction_list = get_transaction_list(user_data)
    transaction_list.append(transaction)
    del user_data['current_transaction']


def build_journal(user_data):
    transaction_list = get_transaction_list(user_data)

    if not transaction_list:
        return "There are no transactions."

    return '\n\n'.join(
        format_transaction(transaction, beancount=True)
        for transaction in transaction_list
    )


def build_report_dict(user_data):
    config = get_user_config(user_data)
    transaction_list = get_transaction_list(user_data)

    report = defaultdict(
        Decimal,
        {account: Decimal(amount) for account, amount
         in zip(config['account_2'], config['initial'])}
    )

    for transaction in transaction_list:
        account = transaction['account_2']
        amount = transaction['amount']
        report[account] -= amount

    return report


def build_report(user_data):
    report = build_report_dict(user_data)

    return '\n'.join(
        f'{account}    {amount:.2f}' for account, amount
        in report.items()
    )


# Utils
SINGLE_VALUE_SETTINGS = ('currency', 'timezone', 'flag')
MULTI_VALUE_SETTINGS = ('payee', 'account_1', 'account_2', 'initial',
                        'favorites')


def format_user_config(user_config):
    lines = []

    for key, value in user_config.items():
        if key in SINGLE_VALUE_SETTINGS:
            lines.append(f'{key}: {value}')
        elif key in MULTI_VALUE_SETTINGS:
            value_list = value
            lines.append(f'{key}:')
            prefix = '    - '

            for value in value_list:
                lines.append(f'{prefix}{value}')

    return '\n'.join(lines)


def get_field_name(field):
    return {
        'payee': 'Payee',
        'account_1': "Expense account",
        'account_2': "Asset account",
        'info': "Info",
    }[field]


def get_default_user_config():
    return dict(
        currency='USD',
        timezone='UTC',
        flag='*',
        payee=['Store', 'Restaurant', 'Taxi'],
        account_1=['Expenses:Stuff', 'Expenses:Food',
                   'Expenses:Transportation'],
        account_2=['Assets:Cash', 'Assets:Bank'],
        initial=['0.00', '0.00'],
        favorites=['Lunch 12.00'],
    )


def set_default_config_values(user_config):
    default_config = get_default_user_config()

    for key in default_config:
        if key not in user_config:
            user_config[key] = default_config[key]


def get_user_config(user_data):
    user_config = user_data.setdefault('config', {})
    set_default_config_values(user_config)
    return user_config


def set_config_field(user_config, field, value):
    value = value.strip()

    if field in SINGLE_VALUE_SETTINGS:
        if field == 'timezone':
            try:
                pytz.timezone(value)
            except pytz.UnknownTimeZoneError:
                raise ValueError("Unknown time zone")

        user_config[field] = value
    elif field in MULTI_VALUE_SETTINGS:
        values = list(filter(None, value.split('\n')))
        if not values:
            raise ValueError("Not enough values")

        if field == 'initial':
            n = len(user_config['account_2'])
            if len(values) != len(user_config['account_2']):
                raise ValueError(f"I need {n} initial amounts")
            try:
                [Decimal(x) for x in values]
            except (ValueError, InvalidOperation):
                raise ValueError(f"Got an invalid amount")

        user_config[field] = values
    else:
        raise ValueError("Unknown setting")


def update_initial_amounts(user_data):
    report = build_report_dict(user_data)
    config = get_user_config(user_data)

    for i, account in enumerate(config['account_2']):
        config['initial'][i] = '{0:.2f}'.format(report[account])


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

    @staticmethod
    def make_config_inline_keyboard():
        user_config = get_default_user_config()
        labels = list(user_config.keys())

        return KeyboardFactory._make_inline_keyboard(
            [*labels, 'Cancel'],
            [*labels, 'cancel']
        )

    @staticmethod
    def make_cancel_button():
        return KeyboardFactory._make_inline_keyboard(
            ['Cancel'], ['cancel'], cols=1
        )

    @staticmethod
    def make_favorite_keyboard(favorites):
        return ReplyKeyboardMarkup.from_column(
            favorites,
            one_time_keyboard=True,
        )


def clear_inline_keyboard(update):
    update.callback_query.edit_message_reply_markup(
        InlineKeyboardMarkup([[]])
    )


def extract_index(data):
    idx = data.split('_')[-1]
    return int(idx)


# States
(WAITING_TRANSACTION, SELECTING_FIELD, FILLING_DATA,
 SELECTING_CONFIG, FILLING_CONFIG) = range(5)


def send_message_and_keyboard(update, message, inline_keyboard=None,
                              do_update=False):
    if inline_keyboard is None:
        inline_keyboard = InlineKeyboardMarkup([[]])

    if do_update:
        update.callback_query.edit_message_text(message,
                                                reply_markup=inline_keyboard)
    else:
        update.message.reply_text(message,
                                  reply_markup=inline_keyboard)


def send_transaction_and_keyboard(update, transaction, inline_keyboard=None,
                                  do_update=False):
    if inline_keyboard is None:
        inline_keyboard = KeyboardFactory.make_main_inline_keyboard()

    formatted_transaction = format_transaction(transaction)

    send_message_and_keyboard(update, formatted_transaction,
                              inline_keyboard=inline_keyboard,
                              do_update=do_update)


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


def start(update, context):
    update.message.reply_text(
        "Hi! I'm BeanBot. Help will go here, but it hasn't been written yet.",
    )

    return WAITING_TRANSACTION


def send_journal(update, context):
    journal = build_journal(context.user_data)
    file = BytesIO()
    file.write(journal.encode('utf-8'))
    file.seek(0)
    update.message.reply_document(file, filename='journal.txt')

    return WAITING_TRANSACTION


def send_report(update, context):
    report = build_report(context.user_data)
    update.message.reply_text(report)

    return WAITING_TRANSACTION


def clear_journal(update, context):
    update_initial_amounts(context.user_data)

    try:
        del context.user_data['transaction_list']
    except KeyError:
        pass

    update.message.reply_text('Cleared!')

    return WAITING_TRANSACTION


def send_config(update, context):
    config = get_user_config(context.user_data)
    config_str = format_user_config(config)

    update.message.reply_text(config_str)

    return WAITING_TRANSACTION


def edit_config(update, context):
    keyboard = KeyboardFactory.make_config_inline_keyboard()

    send_message_and_keyboard(update, "Select setting to edit",
                              inline_keyboard=keyboard)

    return SELECTING_CONFIG


def selecting_config(update, context):
    button = update.callback_query.data

    if button == 'cancel':
        clear_inline_keyboard(update)
        update.callback_query.edit_message_text(
            "You can continue writing transactions."
        )
        update.callback_query.answer('Canceled!')

        return WAITING_TRANSACTION

    context.user_data['config_field'] = button
    keyboard = KeyboardFactory.make_cancel_button()

    send_message_and_keyboard(update, f"Write a value for {button}",
                              inline_keyboard=keyboard, do_update=True)
    update.callback_query.answer("Waiting for value")

    return FILLING_CONFIG


def filling_config(update, context):
    user_config = get_user_config(context.user_data)
    current_config_field = context.user_data['config_field']
    value = update.message.text

    try:
        set_config_field(user_config, current_config_field, value)
    except ValueError as ex:
        send_message_and_keyboard(update, f'Error: {ex}\nTry again.')
        return FILLING_CONFIG

    send_message_and_keyboard(update, 'Config updated!')

    del context.user_data['config_field']
    return WAITING_TRANSACTION


def send_keyboard(update, context):
    user_config = get_user_config(context.user_data)
    keyboard = KeyboardFactory.make_favorite_keyboard(user_config['favorites'])

    update.message.reply_text(
        "Here is your keyboard",
        reply_markup=keyboard,
    )

    return WAITING_TRANSACTION


def cancel_config(update, context):
    button = update.callback_query.data

    if button == 'cancel':
        clear_inline_keyboard(update)
        update.callback_query.edit_message_text(
            "You can continue writing transactions."
        )
        update.callback_query.answer('Canceled!')

        return WAITING_TRANSACTION

    logger.error("Got unexpected callback query")
    return WAITING_TRANSACTION


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def fallback(update, context):
    update.message.reply_text("I got lost. Can try again?")
    return WAITING_TRANSACTION


def main():
    # Create a persistence object
    persistence = PicklePersistence(filename='db.pickle',
                                    store_chat_data=False)

    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN, persistence=persistence, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states
    start_handlers = [
        MessageHandler(Filters.text, register_transaction,
                       pass_user_data=True),
        CommandHandler('start', start),
        CommandHandler('journal', send_journal, pass_user_data=True),
        CommandHandler('clear', clear_journal, pass_user_data=True),
        CommandHandler('config', send_config, pass_user_data=True),
        CommandHandler('edit_config', edit_config, pass_user_data=True),
        CommandHandler('report', send_report, pass_user_data=True),
        CommandHandler('keyboard', send_keyboard, pass_user_data=True),
    ]

    conv_handler = ConversationHandler(
        entry_points=start_handlers,
        states={
            WAITING_TRANSACTION: start_handlers,
            SELECTING_FIELD: [CallbackQueryHandler(selecting_field,
                                                   pass_user_data=True)],
            FILLING_DATA: [CallbackQueryHandler(filling_data_button,
                                                pass_user_data=True),
                           MessageHandler(Filters.text, filling_data_text,
                                          pass_user_data=True)],
            SELECTING_CONFIG: [CallbackQueryHandler(selecting_config,
                                                    pass_user_data=True)],
            FILLING_CONFIG: [MessageHandler(Filters.text, filling_config,
                                            pass_user_data=True),
                             CallbackQueryHandler(cancel_config,
                                                  pass_user_data=True)],
        },
        fallbacks=[MessageHandler(Filters.text, fallback,
                                  pass_user_data=True)],
        persistent=True, name='beanbot_conversation_handler'
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
