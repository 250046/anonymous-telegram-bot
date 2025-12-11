import os
import sys
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for Windows event loop policy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get credentials from environment variables
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_text = (
        "👋 Welcome to the Anonymous Confession Bot!\n\n"
        "📝 How it works:\n"
        "• Send me any message (text, photo, etc.)\n"
        "• I'll post it anonymously to our channel\n"
        "• Your identity stays completely private\n\n"
        "⚠️ Please be respectful and follow community guidelines.\n\n"
        "Type /help for more information."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help is issued."""
    help_text = (
        "ℹ️ How to use this bot:\n\n"
        "📱 In Private Chat:\n"
        "• Send me any message (text, photo, etc.)\n"
        "• I'll post it anonymously to the channel\n\n"
        "💬 In Group Comments:\n"
        "• Use /anon [your message] to post anonymously\n"
        "• Reply to a message and use /anon [your message] to reply anonymously\n\n"
        "📌 Supported content:\n"
        "• Text messages\n"
        "• Photos with captions\n"
        "• Videos, voice messages, stickers\n\n"
        "❌ Rules:\n"
        "• Be respectful\n"
        "• No spam or harassment\n"
        "• No illegal content\n\n"
        "Questions? Contact the channel admin."
    )
    await update.message.reply_text(help_text)

async def anon_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /anon command in group for anonymous comments."""
    try:
        message = update.message
        
        # Only work in the designated group
        if str(message.chat.id) != GROUP_ID:
            return
        
        # Get the message text after /anon
        if not context.args:
            await message.reply_text("⚠️ Usage: /anon [your message]")
            await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            return
        
        anon_text = ' '.join(context.args)
        
        # Check if this is a reply to another message
        reply_to_message_id = None
        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id
        
        # Delete the original message with /anon command
        await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        
        # Send the anonymous message
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=anon_text,
            reply_to_message_id=reply_to_message_id
        )
        
        logger.info(f"Anonymous comment posted in group by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error handling /anon command: {e}")
        try:
            await message.reply_text("❌ Error posting anonymous message.")
        except:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and post them anonymously to the channel."""
    try:
        # Only process private chats
        if update.message.chat.type != 'private':
            return
        
        message = update.message
        sent_message = None
        
        # Handle text messages
        if message.text:
            sent_message = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message.text
            )
        
        # Handle photos
        elif message.photo:
            photo = message.photo[-1]  # Get highest resolution
            caption = message.caption or ""
            sent_message = await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo.file_id,
                caption=caption
            )
        
        # Handle videos
        elif message.video:
            caption = message.caption or ""
            sent_message = await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=message.video.file_id,
                caption=caption
            )
        
        # Handle voice messages
        elif message.voice:
            sent_message = await context.bot.send_voice(
                chat_id=CHANNEL_ID,
                voice=message.voice.file_id
            )
        
        # Handle stickers
        elif message.sticker:
            sent_message = await context.bot.send_sticker(
                chat_id=CHANNEL_ID,
                sticker=message.sticker.file_id
            )
        
        # Handle documents
        elif message.document:
            caption = message.caption or ""
            sent_message = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=message.document.file_id,
                caption=caption
            )
        
        else:
            await message.reply_text(
                "⚠️ Sorry, this type of content is not supported yet.\n"
                "Please send text, photos, videos, or voice messages."
            )
            return
        
        # Create delete button with message ID
        keyboard = [[InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{sent_message.message_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Confirm to user with delete button
        await message.reply_text(
            "✅ Your message has been posted anonymously!",
            reply_markup=reply_markup
        )
        logger.info(f"Message posted to channel from user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await message.reply_text(
            "❌ Sorry, there was an error posting your message. Please try again later."
        )

async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete button callback."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract message ID from callback data
        message_id = int(query.data.split('_')[1])
        
        # Delete the message from channel
        await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=message_id)
        
        # Update the confirmation message
        await query.edit_message_text("🗑️ Your message has been deleted from the channel.")
        logger.info(f"Message {message_id} deleted by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        await query.edit_message_text("❌ Failed to delete the message. It may have already been deleted.")

async def main():
    """Start the bot."""
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID environment variables")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("anon", anon_command))
    application.add_handler(CallbackQueryHandler(delete_callback, pattern="^delete_"))
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))
    
    # Start the bot
    logger.info("Bot started successfully!")
    
    # Initialize and start polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
