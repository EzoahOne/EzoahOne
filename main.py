import os
import logging
import re
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

app = Flask(__name__)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states
CHOOSE_BUNDLE, ENTER_PHONE, CONFIRM_RECEIPT = range(3)

# Define your worker's Telegram user ID and your own Telegram user ID
WORKER_ID = 349002878
YOUR_ID = 2058207928

# Define your MoMo number
MOMO_NUMBER = '0543226313'

# Define a dictionary to store user data temporarily
user_data = {}

# Define the data bundles with prices
data_bundles = {
    '10GB': 'GHC 72',
    '15GB': 'GHC 92',
    '20GB': 'GHC 113',
    '25GB': 'GHC 142',
    '30GB': 'GHC 158',
    '40GB': 'GHC 195',
    '50GB': 'GHC 247',
}

@app.route('/')
def index():
    return 'Welcome to my Telegram bot!'

@app.route(f'/{os.getenv("TELEGRAM_TOKEN")}/webhook', methods=['POST'])
def webhook():
    """Set up the webhook endpoint for Telegram"""
    update = Update.de_json(request.get_json(force=True), updater.bot)
    updater.dispatcher.process_update(update)
    return 'OK'

def start(update, context):
    """Send a message when the command /start is issued."""
    keyboard = [
        [
            InlineKeyboardButton("10 GB - GHC 72", callback_data='10GB'),
            InlineKeyboardButton("15 GB - GHC 92", callback_data='15GB'),
        ],
        [
            InlineKeyboardButton("20 GB - GHC 113", callback_data='20GB'),
            InlineKeyboardButton("25 GB - GHC 142", callback_data='25GB'),
        ],
        [
            InlineKeyboardButton("30 GB - GHC 158", callback_data='30GB'),
            InlineKeyboardButton("40 GB - GHC 195", callback_data='40GB'),
        ],
        [
            InlineKeyboardButton("50 GB - GHC 247", callback_data='50GB'),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose a data bundle package:', reply_markup=reply_markup)
    return CHOOSE_BUNDLE

def choose_bundle(update, context):
    """Save the chosen bundle and ask for phone number."""
    query = update.callback_query
    query.answer()

    user_data[query.from_user.id] = {'bundle': query.data, 'price': data_bundles[query.data]}

    query.edit_message_text(
        text=f"Selected bundle: {query.data} - {data_bundles[query.data]}\nPlease enter the beneficiary's phone number:"
    )
    return ENTER_PHONE

def enter_phone(update, context):
    """Save phone number and send payment details."""
    user_id = update.message.from_user.id
    phone_number = update.message.text

    # Validate phone number (only digits and length check)
    if not re.match(r'^\d+$', phone_number) or len(phone_number) < 7 or len(phone_number) > 15:
        update.message.reply_text('Please enter a valid phone number (digits only).')
        return ENTER_PHONE

    # Get bundle and price from user_data
    bundle = user_data[user_id]['bundle']
    price = user_data[user_id]['price']

    user_data[user_id]['phone_number'] = phone_number

    # Send order details to worker
    worker_message = f"New order received\nBundle: {bundle}\nBeneficiary's phone number: {phone_number}"
    try:
        context.bot.send_message(chat_id=WORKER_ID, text=worker_message)
        logger.info(f"Sent message to worker: {worker_message}")
    except Exception as e:
        logger.error(f"Failed to send message to worker: {e}")

    # Send order details to user
    user_message = f"New order received\nBundle: {bundle} - {price}\nBeneficiary's phone number: {phone_number}"
    try:
        context.bot.send_message(chat_id=YOUR_ID, text=user_message, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Payment Made", callback_data=f'payment_{user_id}')]]
        ))
        logger.info(f"Sent message to you: {user_message}")
    except Exception as e:
        logger.error(f"Failed to send message to you: {e}")

    # Send MoMo number for payment
    update.message.reply_text(f'Please make the payment of {price} to the following MoMo number: {MOMO_NUMBER}')
    logger.info(f"Requested payment from user {user_id}")
    return CONFIRM_RECEIPT

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(token, use_context=True)
    
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CallbackQueryHandler(choose_bundle, pattern=r'^\d+GB$'))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, enter_phone))
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
