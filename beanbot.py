#!/usr/bin/env python

import datetime
import decimal
import itertools
import logging
import os
import re

from telegram import (ReplyKeyboardMarkup, InlineKeyboardButton,
                      InlineKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, RegexHandler, ConversationHandler,
                          CallbackQueryHandler)


# Token
TOKEN = os.environ.get('BOT_TOKEN')


# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Models
def create_new_transaction(**kwargs):
    transaction = {
        'date': datetime.date.today(),
        'info': '',
        'payee': '',
        'flag': '*',
        'currency': 'PEN',
        'account_1': 'Expenses:Stuff',
        'amount': decimal.Decimal(0),
        'account_2': 'Assets:Cash',
    }
    transaction.update(kwargs)
    return transaction


def parse_message_transaction(text):
    *info, amount, currency = text.split()

    return create_new_transaction(
        info=' '.join(info),
        amount=decimal.Decimal(amount),
        currency=currency,
    )


class Default:
    payee = ['Metro', 'Sr. Roos', 'Grocery store', 'Restaurant', 'La Panetteria']


# Utils
def make_main_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('Payee', callback_data='payee'),
         InlineKeyboardButton('Info', callback_data='info')],
        [InlineKeyboardButton('Asset', callback_data='account_1'),
         InlineKeyboardButton('Expense', callback_data='account_2')],
        [InlineKeyboardButton('Done!', callback_data='done')]
    ])


class KeyboardFactory:
    @staticmethod
    def _make_2x3_keyboard(labels, data):
        pairs = zip(labels, data)
        cols = 2
        rows = len(data) // 2 + len(data) % 2

        # return [
        #     [InlineKeyboardButton(*pair)
        #      for pair in itertools.islice(pairs, start, start + cols)]
        #     for start in range(rows)
        # ]

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(labels[0], callback_data=data[0]),
             InlineKeyboardButton(labels[1], callback_data=data[1])],
            [InlineKeyboardButton(labels[2], callback_data=data[2]),
             InlineKeyboardButton(labels[3], callback_data=data[3])],
            [InlineKeyboardButton(labels[4], callback_data=data[4]),
             InlineKeyboardButton(labels[5], callback_data=data[5])],
        ])

    @staticmethod
    def get_kb_for_payee():
        data = ['payee_{}'.format(i) for i in range(len(Default.payee))]
        return KeyboardFactory._make_2x3_keyboard(
            (*Default.payee, '« Back'), (*data, 'go_back'))


# States
WAITING_TRANSACTION, SELECTING_FIELD, FILLING_DATA = range(3)


def format_transaction(transaction):
    return ("{date} {flag} {payee} {info}\n"
            "    {account_1}    {amount} {currency}\n"
            "    {account_2}").format(
                **transaction
            )


def start(update, context):
    update.message.reply_text(
        "Hi! I'm BeanBot. Help will go here, but it hasn't been written yet.",
    )

    return WAITING_TRANSACTION


def register_transaction(update, context):
    try:
        transaction = parse_message_transaction(update.message.text)
    except Exception as ex:
        update.message.reply_text("I couldn't understand that "
                                  "because {}".format(ex))
        logger.exception(ex)
        return WAITING_TRANSACTION

    inline_keyboard = make_main_inline_keyboard()
    formatted_transaction = format_transaction(transaction)

    context.user_data['current_transaction'] = transaction

    update.message.reply_text(formatted_transaction,
                              reply_markup=inline_keyboard)

    return SELECTING_FIELD


def selecting_field(update, context):
    button = update.callback_query.data
    current_transaction = context.user_data['current_transaction']

    if button == 'done':  # commit transaction
        transaction_list = context.user_data.setdefault('transaction_list', [])

        transaction_list.append(current_transaction)

        del context.user_data['current_transaction']

        update.callback_query.edit_message_reply_markup(
            InlineKeyboardMarkup(
                [[InlineKeyboardButton('Edit', callback_data='edit')]]
            )
        )

        update.callback_query.answer('Saved!')

        return WAITING_TRANSACTION

    current_transaction[button] = '[{}]'.format(button.title())

    context.user_data['field'] = button

    update.callback_query.edit_message_text(
        format_transaction(current_transaction)
    )

    method_name = f'get_kb_for_{button}'
    method = getattr(KeyboardFactory, method_name, None)
    keyboard = method and method()

    if keyboard is not None:
        update.callback_query.edit_message_reply_markup(
            keyboard
        )

    update.callback_query.answer('Select one option')

    return FILLING_DATA


def filling_data(update, context):
    button = update.callback_query.data
    current_transaction = context.user_data['current_transaction']
    current_field = context.user_data['field']

    try:
        index = int(button.split('_')[-1])
        list_ = getattr(Default, current_field, [])
        current_transaction[current_field] = list_[index]
    except Exception as ex:
        update.callback_query.answer("That didn't work because {}".format(ex))
        logger.exception(ex)
    else:
        update.callback_query.edit_message_text(
            format_transaction(current_transaction)
        )

    update.callback_query.edit_message_reply_markup(
        make_main_inline_keyboard()
    )

    return SELECTING_FIELD


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def fallback(update, context):
    update.message.reply_text('Fallback!')
    return WAITING_TRANSACTION


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text, register_transaction,
                                     pass_user_data=True)],
        states={
            WAITING_TRANSACTION: [MessageHandler(Filters.text, register_transaction,
                                                 pass_user_data=True)],
            SELECTING_FIELD: [CallbackQueryHandler(
                                             selecting_field,
                                             pass_user_data=True)],
            FILLING_DATA: [CallbackQueryHandler(
                                          filling_data,
                                          pass_user_data=True),
                           ],
        },
        fallbacks=[MessageHandler(Filters.text, fallback, pass_user_data=True)],
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
