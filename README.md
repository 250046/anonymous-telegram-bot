# Anonymous Telegram Bot

A Telegram bot that receives private messages and posts them anonymously to a channel.

## Features

- ✅ Anonymous message forwarding
- ✅ Supports text, photos, videos, voice messages, stickers, and documents
- ✅ Simple commands: `/start` and `/help`
- ✅ Privacy-focused: no user information is revealed
- ✅ 24/7 uptime on Railway

## Setup

### Prerequisites

1. Telegram Bot Token from [@BotFather](https://t.me/BotFather)
2. Telegram Channel with bot added as admin (with "Post Messages" permission)
3. Channel ID (numeric ID like `-1001234567890`)

### Local Testing

1. Install Python 3.11+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials
4. Run the bot:
   ```bash
   python bot.py
   ```

### Deploy to Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository
3. Add environment variables in Railway dashboard:
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `TELEGRAM_CHANNEL_ID`: Your channel ID
4. Railway will automatically detect the `Procfile` and deploy

The bot will start automatically and run 24/7!

## Usage

1. Users send a private message to the bot
2. Bot posts the message anonymously to the channel
3. User receives confirmation

## Commands

- `/start` - Welcome message and instructions
- `/help` - Detailed help and rules

## Project Structure

```
.
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── Procfile           # Railway startup command
├── runtime.txt        # Python version
├── .env.example       # Example environment variables
└── README.md          # This file
```

## Security Notes

- Never commit `.env` file to git (it's in `.gitignore`)
- Use Railway's environment variables for production
- Bot logs user IDs internally for moderation but never exposes them publicly
