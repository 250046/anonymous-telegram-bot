import os
import sys
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from openai import OpenAI

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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

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
        "↩️ Reply to Channel Posts:\n"
        "• Right-click a channel message → 'Reply in another chat'\n"
        "• Select this bot and type your reply\n"
        "• Your reply will be posted with a quote-link!\n\n"
        "💬 In Group Comments:\n"
        "• Use /anon [your message] to post anonymously\n"
        "• Reply to a message and use /anon [your message] to reply anonymously\n\n"
        "📌 Supported content:\n"
        "• Text messages\n"
        "• Photos (single or multiple)\n"
        "• Videos, voice messages, stickers\n"
        "• Audio files (mp3, etc.)\n"
        "• Polls\n"
        "• Documents\n\n"
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
        user_id = update.effective_user.id
        
        # Only work in the designated group
        if str(message.chat.id) != GROUP_ID:
            return
        
        # Get the message text after /anon
        if not context.args:
            await message.reply_text("⚠️ Usage: /anon [your message]")
            await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            return
        
        anon_text = ' '.join(context.args)
        
        # Format the message with "via /anon" in monospace
        formatted_text = f"{anon_text}\n\nvia `/anon`"
        
        # Check if this is a reply to another message
        reply_to_message_id = None
        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id
        
        # Delete the original message with /anon command
        await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        
        # Create delete button - encode user_id so only sender can delete
        keyboard = [[InlineKeyboardButton("🗑️", callback_data=f"anondelete_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the anonymous message with delete button
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=formatted_text,
            reply_to_message_id=reply_to_message_id,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"Anonymous comment posted in group by user {user_id}")
        
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
        sent_messages = []  # For media groups
        reply_to_message_id = None
        
        # Check if this is a reply to a channel message (via "Reply in another chat")
        if message.external_reply:
            ext_reply = message.external_reply
            # Check if it's from our channel
            if ext_reply.chat and str(ext_reply.chat.id) == CHANNEL_ID:
                reply_to_message_id = ext_reply.message_id
                logger.info(f"Detected reply to channel message {reply_to_message_id}")
        
        # Also check for quote (another way Telegram sends this info)
        if message.quote and not reply_to_message_id:
            # Quote contains the original message info
            if hasattr(message, 'reply_to_message') and message.reply_to_message:
                if message.reply_to_message.forward_origin:
                    origin = message.reply_to_message.forward_origin
                    if hasattr(origin, 'chat') and str(origin.chat.id) == CHANNEL_ID:
                        reply_to_message_id = origin.message_id
        
        # Check minimum length for text messages
        if message.text and len(message.text.strip()) < 10:
            await message.reply_text(
                "❌ Your message is too short.\n\n"
                "Please send at least 10 characters to post anonymously."
            )
            return
        
        # Handle media groups (multiple photos/videos in one message)
        if message.media_group_id:
            media_group_id = message.media_group_id
            user_id = update.effective_user.id
            
            # Initialize storage for this media group
            if 'media_groups' not in context.bot_data:
                context.bot_data['media_groups'] = {}
            
            key = f"{user_id}_{media_group_id}"
            
            if key not in context.bot_data['media_groups']:
                context.bot_data['media_groups'][key] = {
                    'media': [],
                    'caption': None,
                    'chat_id': message.chat.id,
                    'reply_to_message_id': reply_to_message_id
                }
            
            # Add media to group
            from telegram import InputMediaPhoto, InputMediaVideo
            if message.photo:
                media_item = InputMediaPhoto(media=message.photo[-1].file_id)
                context.bot_data['media_groups'][key]['media'].append(media_item)
            elif message.video:
                media_item = InputMediaVideo(media=message.video.file_id)
                context.bot_data['media_groups'][key]['media'].append(media_item)
            
            # Capture caption from first message with caption
            if message.caption and not context.bot_data['media_groups'][key]['caption']:
                context.bot_data['media_groups'][key]['caption'] = message.caption
            
            # Schedule sending after a short delay to collect all media
            async def send_media_group_delayed():
                await asyncio.sleep(1)  # Wait for all media to arrive
                if key in context.bot_data['media_groups']:
                    group_data = context.bot_data['media_groups'].pop(key)
                    if group_data['media']:
                        # Set caption on first media item
                        if group_data['caption']:
                            group_data['media'][0].caption = group_data['caption']
                        
                        sent_msgs = await context.bot.send_media_group(
                            chat_id=CHANNEL_ID,
                            media=group_data['media'],
                            reply_to_message_id=group_data['reply_to_message_id']
                        )
                        
                        # Create delete button for first message
                        keyboard = [[InlineKeyboardButton("🗑️ Delete All", callback_data=f"deletegroup_{sent_msgs[0].message_id}_{len(sent_msgs)}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await context.bot.send_message(
                            chat_id=group_data['chat_id'],
                            text="✅ Your media group has been posted anonymously!",
                            reply_markup=reply_markup
                        )
                        logger.info(f"Media group posted to channel from user {user_id}")
            
            # Only schedule once per media group
            if len(context.bot_data['media_groups'][key]['media']) == 1:
                asyncio.create_task(send_media_group_delayed())
            return
        
        # Handle text messages
        if message.text:
            sent_message = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message.text,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle photos (single)
        elif message.photo:
            photo = message.photo[-1]  # Get highest resolution
            caption = message.caption or ""
            sent_message = await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle videos
        elif message.video:
            caption = message.caption or ""
            sent_message = await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=message.video.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle voice messages
        elif message.voice:
            sent_message = await context.bot.send_voice(
                chat_id=CHANNEL_ID,
                voice=message.voice.file_id,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle audio files (mp3, etc.)
        elif message.audio:
            caption = message.caption or ""
            sent_message = await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=message.audio.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle polls
        elif message.poll:
            poll = message.poll
            sent_message = await context.bot.send_poll(
                chat_id=CHANNEL_ID,
                question=poll.question,
                options=[opt.text for opt in poll.options],
                is_anonymous=poll.is_anonymous,
                type=poll.type,
                allows_multiple_answers=poll.allows_multiple_answers,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle stickers
        elif message.sticker:
            sent_message = await context.bot.send_sticker(
                chat_id=CHANNEL_ID,
                sticker=message.sticker.file_id,
                reply_to_message_id=reply_to_message_id
            )
        
        # Handle documents
        elif message.document:
            caption = message.caption or ""
            sent_message = await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=message.document.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        else:
            await message.reply_text(
                "⚠️ Sorry, this type of content is not supported yet.\n"
                "Please send text, photos, videos, audio, polls, or voice messages."
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
    
    try:
        data_parts = query.data.split('_')
        
        # Handle /anon message deletion in group
        if data_parts[0] == 'anondelete':
            allowed_user_id = int(data_parts[1])
            clicking_user_id = update.effective_user.id
            
            # Check if the clicking user is the original sender
            if clicking_user_id != allowed_user_id:
                await query.answer("❌ Only the sender can delete this message.", show_alert=True)
                return
            
            await query.answer()
            # Delete the anon message from group
            await context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
            logger.info(f"Anon message deleted by user {clicking_user_id}")
            return
        
        await query.answer()
        
        # Handle media group deletion
        if data_parts[0] == 'deletegroup':
            first_message_id = int(data_parts[1])
            count = int(data_parts[2])
            
            # Delete all messages in the media group
            for i in range(count):
                try:
                    await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=first_message_id + i)
                except Exception:
                    pass  # Some messages might already be deleted
            
            await query.edit_message_text("🗑️ Your media group has been deleted from the channel.")
            logger.info(f"Media group starting at {first_message_id} deleted by user {update.effective_user.id}")
        
        # Handle single message deletion
        else:
            message_id = int(data_parts[1])
            await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=message_id)
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
    application.add_handler(CallbackQueryHandler(delete_callback, pattern="^deletegroup_"))
    application.add_handler(CallbackQueryHandler(delete_callback, pattern="^anondelete_"))
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
