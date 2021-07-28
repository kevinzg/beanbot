import logging
import os
import traceback
from typing import Optional

import telegram
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    PicklePersistence,
    Updater,
)

from . import db as database
from . import formatter, parser
from .errors import UserError
from .models import Posting, Transaction, UserConfig


# Config


load_dotenv()

TOKEN = os.environ.get('BOT_TOKEN')
DB_PATH = os.environ.get('DB_PATH') or 'db.pickle'


# Logging


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


# Main function


def run():
    # Create a persistence object
    persistence = PicklePersistence(filename=DB_PATH, store_chat_data=False)

    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN, persistence=persistence)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add message handlers
    dp.add_handler(CommandHandler('start', handle_start_command))
    dp.add_handler(MessageHandler(Filters.text, handle_text_message))
    dp.add_handler(CallbackQueryHandler(handle_inline_button))

    # Log all errors
    dp.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


# Messages handlers


def handle_start_command(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(
        "Hi! I'm Beanbot. I can help you keep track of your financial transactions.",
    )


def handle_text_message(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        event = parser.parse_message(update.message.text)
        event.message_id = update.message.message_id
    except UserError as ex:
        update.message.reply_text(str(ex))
        return

    # Process
    db = database.DB(context.user_data)
    tx, posting = db.process_event(event)

    tx_string = formatter.format_transaction(tx)
    keyboard = make_actions_keyboard(db.config, tx, posting)

    update.message.reply_text(
        tx_string, parse_mode=telegram.ParseMode.MARKDOWN_V2, reply_markup=keyboard
    )


def handle_inline_button(update: telegram.Update, context: telegram.ext.CallbackContext):
    keyboard_data = update.callback_query.data

    if keyboard_data == 'done':
        update.callback_query.edit_message_reply_markup()
        return

    event = parser.parse_keyboard_data(update.callback_query.data)
    event.message_id = update.callback_query.message.message_id

    db = database.DB(context.user_data)
    tx, posting = db.process_event(event)

    if event.action == 'delete':
        message = f'{posting.debit_account} {posting.amount}~' if posting is not None else tx.info
        update.callback_query.edit_message_text(
            f'~{message}~',
            parse_mode=telegram.ParseMode.MARKDOWN_V2,
            reply_markup=EMPTY_KEYBOARD,
        )
        return

    tx_string = formatter.format_transaction(tx)
    keyboard = make_actions_keyboard(db.config, tx, posting)

    update.callback_query.edit_message_text(
        tx_string, parse_mode=telegram.ParseMode.MARKDOWN_V2, reply_markup=keyboard
    )


# Error handler


def error_handler(update: telegram.Update, context: telegram.ext.CallbackContext):
    error = context.error

    def reply_text(message: str):
        if update.message is not None:
            update.message.reply_text(message)
        elif update.callback_query is not None:
            update.callback_query.reply_text(message)
        else:
            raise Exception('Update has no message nor callback query')

    if isinstance(error, UserError):
        logger.warning('Update "%s" caused user error "%s".', update, error)
        reply_text(str(error))
        return

    trace = traceback.format_exception(
        type(error),
        error,
        error.__traceback__,
    )
    logger.error(
        'Update "%s" caused error "%s".\nTraceback:\n%s', update, context.error, ''.join(trace)
    )
    reply_text(f'Internal error: {error}')


# Keyboards


EMPTY_KEYBOARD = InlineKeyboardMarkup([[]])


def make_actions_keyboard(config: UserConfig, tx: Transaction, posting: Optional[Posting]):
    rows = []

    # Basic buttons
    rows.append(
        [
            InlineKeyboardButton('Delete', 'delete'),
            InlineKeyboardButton('Done', 'done'),
        ]
    )

    if posting is not None:
        # Payment methods
        rows.append(
            [
                InlineKeyboardButton(acc, f'acc_{idx}')
                for idx, acc in enumerate(config.credit_accounts)
                if acc != posting.credit_account
            ]
        )

        # Currency
        rows.append(
            [
                InlineKeyboardButton(cur, f'cur_{idx}')
                for idx, cur in enumerate(config.currencies)
                if cur != posting.currency
            ]
        )

    return InlineKeyboardMarkup(rows)
