import codecs
import json
import logging
import os
import textwrap
import traceback
from dataclasses import asdict
from datetime import datetime
from io import BytesIO
from typing import Optional

import pytz
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
from .models import Action, Posting, Transaction, UserConfig


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
    dp.add_handler(CommandHandler('json', handle_json_command))
    dp.add_handler(CommandHandler('clear', handle_clear_command))
    dp.add_handler(CommandHandler('config', handle_config_command))
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


# Command handlers


def handle_start_command(update: telegram.Update, context: telegram.ext.CallbackContext):
    update.message.reply_text(
        "Hi! I'm Beanbot. I can help you keep track of your financial transactions.",
    )


def handle_json_command(update: telegram.Update, context: telegram.ext.CallbackContext):
    db = database.DB(context.user_data)

    date = datetime.now(tz=db.config.tzinfo).strftime('%Y-%m-%d-%H-%M-%S')
    filename = f'beanbot-{date}.json'

    def transform(value):
        if isinstance(value, datetime):
            return value.isoformat()
        else:
            return f'{value}'

    data = list(map(asdict, db.transactions))

    StreamWriter = codecs.getwriter('utf-8')
    file = BytesIO()
    json.dump(data, StreamWriter(file), default=transform, indent=4)

    file.seek(0)
    update.message.reply_document(file, filename=filename)


def handle_clear_command(update: telegram.Update, context: telegram.ext.CallbackContext):
    db = database.DB(context.user_data)
    db.clear()

    update.message.reply_text('Cleared!')


def handle_config_command(update: telegram.Update, context: telegram.ext.CallbackContext):
    msg = update.message or update.edited_message

    if not context.args:
        msg.reply_text(
            textwrap.dedent(
                """\
            /config timezone <tz>
            /config currencies <cur 1> [<currencies>]
            /config accounts <acc 1> [<accounts>]
            """
            )
        )
        return

    key, *values = context.args

    if key not in ['timezone', 'currencies', 'accounts']:
        raise UserError(f'Unknown key {key}')

    if key == 'accounts':
        key = 'credit_accounts'

    db = database.DB(context.user_data)

    if not values:
        value = ''
        if key == 'timezone':
            value = db.config.timezone
        else:
            value = '\n'.join(getattr(db.config, key))
        msg.reply_text(value)
        return

    if key == 'timezone':
        tz = values[0]
        try:
            pytz.timezone(tz)
        except pytz.UnknownTimeZoneError:
            raise UserError(f'Invalid IANA timezone: {tz}')
        db.config.timezone = tz
    else:  # lists
        if len(values) > 4:
            raise UserError('Max values allowed are 4')
        if not all(v.strip() for v in values):
            raise UserError('There are invalid values')
        setattr(db.config, key, values)

    msg.reply_text('Updated!')


# Message handlers


def handle_text_message(update: telegram.Update, context: telegram.ext.CallbackContext):
    try:
        event = parser.parse_message(update.message.text)
    except UserError as ex:
        update.message.reply_text(str(ex))
        return

    # Process
    db = database.DB(context.user_data)
    tx, posting = db.process_event(event)

    tx_string = formatter.format_transaction(tx)
    keyboard = make_actions_keyboard(db.config, tx, posting)

    message = update.message.reply_text(
        tx_string, parse_mode=telegram.ParseMode.MARKDOWN_V2, reply_markup=keyboard
    )

    db.update_message_index(message.message_id, tx, posting)


def handle_inline_button(update: telegram.Update, context: telegram.ext.CallbackContext):
    event = parser.parse_keyboard_data(update.callback_query.data)
    event.message_id = update.callback_query.message.message_id

    db = database.DB(context.user_data)
    tx, posting = db.process_event(event)

    if event.action == Action.COMMIT:
        update.callback_query.edit_message_reply_markup(EMPTY_KEYBOARD)
        return
    elif event.action == Action.DELETE:
        message = formatter.escape_markdown(
            f'{posting.debit_account} {posting.amount}' if posting is not None else tx.info
        )
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
        msg = update.message or update.callback_query or update.edited_message
        msg.reply_text(message)

    if isinstance(error, UserError):
        logger.warning('Update "%s" caused user error "%s".', update, error)
        reply_text(str(error))
        return

    trace = traceback.format_exception(
        type(error),
        error,
        error.__traceback__,
    )
    logger.error('Update "%s" caused error "%s".\n%s', update, context.error, ''.join(trace))
    reply_text(f'Internal error: {error}')


# Keyboards


EMPTY_KEYBOARD = InlineKeyboardMarkup([[]])


def make_actions_keyboard(config: UserConfig, tx: Transaction, posting: Optional[Posting]):
    rows = []

    if posting is not None:
        # Payment methods
        rows.append(
            [
                InlineKeyboardButton(acc, callback_data=f'acc_{idx}')
                for idx, acc in enumerate(config.credit_accounts)
                if acc != posting.credit_account
            ]
        )

        # Currency
        rows.append(
            [
                InlineKeyboardButton(cur, callback_data=f'cur_{idx}')
                for idx, cur in enumerate(config.currencies)
                if cur != posting.currency
            ]
        )

    # Basic buttons
    rows.append(
        [
            InlineKeyboardButton('Delete', callback_data='delete'),
            InlineKeyboardButton('Done', callback_data='commit'),
        ]
    )

    return InlineKeyboardMarkup(rows)
