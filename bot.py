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

async def moderate_content(text: str) -> dict:
    """
    Check content for vulgar words using keyword filter + AI backup.
    Returns: {'allowed': bool, 'warning': str or None, 'reason': str or None}
    """
    # Comprehensive vulgar word list (case-insensitive)
    vulgar_words = [
        # English
        'fuck', 'shit', 'dick', 'cock', 'pussy', 'anal', 'bitch', 'ass', 'bastard',
        'cunt', 'whore', 'slut', 'sex', 'penis', 'vagina', 'porn', 'nude',
        # Russian
        'хуй', 'пизда', 'ебать', 'ебал', 'ебаный', 'блять', 'блядь', 'сука', 
        'хер', 'жопа', 'говно', 'срать', 'ссать', 'мудак', 'пидор', 'шлюха',
        # Uzbek
        'qotoq', 'qo\'taq', 'jalap', 'sik', 'sikmoq', 'jinni', 'orospi', 
        'fahisha', 'yalang', 'qo'taq',
    ]
    
    # Check for vulgar words (case-insensitive)
    text_lower = text.lower()
    for word in vulgar_words:
        # Check if word exists as whole word or part of text
        if word in text_lower:
            return {
                'allowed': False, 
                'warning': None, 
                'reason': f'Contains vulgar word: "{word}"'
            }
    
    # If no keywords found, use AI as backup check
    if not openai_client:
        return {'allowed': True, 'warning': None, 'reason': None}
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a backup content moderator for 'PU Freedom'.

ONLY block if you find vulgar/profane words that weren't caught by the keyword filter.
Look for creative spellings, slang, or other crude language.

ALLOW ALL topics - only block vulgar WORDS.

Respond in JSON format:
{
  "action": "allow" | "block",
  "reason": "brief explanation if blocked"
}"""
                },
                {
                    "role": "user",
                    "content": f"Check this message:\n\n{text}"
                }
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        if result['action'] == 'block':
            return {'allowed': False, 'warning': None, 'reason': result['reason']}
        else:
            return {'allowed': True, 'warning': None, 'reason': None}
            
    except Exception as e:
        logger.error(f"Moderation error: {e}")
        # On error, allow the message (fail open, not closed)
        return {'allowed': True, 'warning': None, 'reason': None}

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
        
        # Moderate text content
        content_to_check = message.text or message.caption or ""
        if content_to_check:
            moderation = await moderate_content(content_to_check)
            
            if not moderation['allowed']:
                await message.reply_text(
                    f"❌ Your message contains vulgar language and was not posted.\n\n"
                    f"Reason: {moderation['reason']}\n\n"
                    f"PU Freedom welcomes all topics and opinions, but please avoid profane words. Rephrase and try again!"
                )
                logger.info(f"Message blocked from user {update.effective_user.id}: {moderation['reason']}")
                return
        
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

async def generate_ai_message() -> str:
    """Generate a realistic anonymous message using AI."""
    if not openai_client:
        return None
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are generating realistic anonymous confessions/messages for a university anonymous channel called 'PU Freedom'.

Generate ONE short, authentic-sounding message that a real student might post anonymously. Mix different types:

Types to rotate:
1. Confessions (crushes, secrets, embarrassing moments)
2. Funny observations about university life
3. Relatable student struggles (exams, sleep, food)
4. Cringe moments or awkward situations
5. Random thoughts or shower thoughts
6. Questions to the community
7. Unpopular opinions
8. Rants about small annoyances

Requirements:
- Keep it SHORT (1-3 sentences max)
- Sound natural and authentic
- No vulgar words
- Relatable to university students
- Mix serious and funny
- Vary the tone and topic

Just return the message text, nothing else."""
                },
                {
                    "role": "user",
                    "content": "Generate one anonymous message:"
                }
            ],
            temperature=0.9,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error generating AI message: {e}")
        return None

async def auto_post_messages(application):
    """Automatically post AI-generated messages every ~6 minutes (10 per hour)."""
    while True:
        try:
            # Wait 6 minutes (360 seconds) between posts
            await asyncio.sleep(360)
            
            # Generate message
            message = await generate_ai_message()
            
            if message:
                # Post to channel
                await application.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message
                )
                logger.info(f"Auto-posted AI message: {message[:50]}...")
            
        except Exception as e:
            logger.error(f"Error in auto-post: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

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
    
    # Start auto-posting in background
    if openai_client:
        asyncio.create_task(auto_post_messages(application))
        logger.info("Auto-posting enabled: 10 messages per hour")
    
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
