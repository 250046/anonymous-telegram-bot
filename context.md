# Context: Anonymous Telegram Bot + Channel (PU-style)

## 1. Overview

We want a Telegram system similar to **PU Anonymous Bot**:

* A **Telegram Bot** that users can DM.
* A **Telegram Channel** where the bot posts messages it receives.
* Messages should appear in the channel as **anonymous posts** (no sender info visible, only the bot/channel).

The bot must run **24/7 on a VPS** (cloud server), not on a local computer.

---

## 2. Goal / Use Case

* Any user sends a **private message** to the bot.
* The bot **forwards or reposts** the message into a specific channel.
* In the channel, the message should look like a **normal channel post**, not like “forwarded from @username”.
* The **user’s identity must never be revealed** in the channel.

Example flow:

1. User → “Hi, I want to confess something…”
2. Bot receives DM.
3. Bot posts to channel:

   > Hi, I want to confess something…

No username, no profile link, nothing that reveals who wrote it.

---

## 3. Functional Requirements

### 3.1 Core Behavior

* The bot should:

  * Accept **text messages** from any user in private chat.
  * Post the text to a **fixed Telegram channel**.
  * Ignore group chats (optional but preferred).

### 3.2 Commands

Minimum:

* `/start`

  * Sends a welcome message explaining:

    * This bot posts your messages anonymously to the channel.
* `/help`

  * Explains:

    * How to use the bot.
    * Any rules (if we define them later).

### 3.3 Message Handling

* Basic version:

  * Take the incoming text message and post it **as-is** to the channel.

* Nice-to-have (optional):

  * If the user sends an empty message or unsupported content, reply with a short error/help text.
  * Optionally support:

    * Photos with captions
    * Stickers, voice, etc. (not required for v1, up to you).

---

## 4. Privacy & Anonymity

* The channel must **never show**:

  * The sender’s username
  * The sender’s display name
  * “Forwarded from …”
* Messages should appear like the bot itself is posting.
* The bot is allowed to log internally (for moderation), but **no public identifying info** should appear in the channel.

---

## 5. Telegram Setup (Assumptions)

We assume the following will be prepared / provided:

1. **Bot Token** from BotFather

   * e.g., `123456789:ABC-DEF...`

2. **Channel**

   * A Telegram channel created for anonymous posts.

3. **Bot as Channel Admin**

   * The bot must be added as **Admin** to the channel with:

     * Permission to **post messages**.

4. **Channel ID**

   * Internal numeric channel ID (e.g. `-1001234567890`) will be provided to the bot via config/env.

If you need a specific format, we can provide:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=-1001234567890
```

---

## 6. Tech Stack & Deployment

### 6.1 Language & Framework

* Preferred: **Python** or **Node.js** (Kiro can pick whichever is more convenient).
* For Python, something like `python-telegram-bot` is OK.
* For Node.js, `node-telegram-bot-api` or similar is OK.

### 6.2 VPS Environment

* OS: **Ubuntu** (e.g., 22.04 LTS) on a cloud VPS.
* VPS Provider: Hetzner / DigitalOcean / Vultr / etc. (any is fine).
* Requirements:

  * Bot must run **24/7**, even if the user’s PC is off.
  * Use a process manager such as:

    * `pm2` (preferred), or
    * `systemd`, or
    * Docker + restart policy.

### 6.3 Project Structure (Suggestion)

Something like:

```text
project-root/
  src/
    bot.(py|js)
  .env.example
  README.md
  requirements.txt or package.json
```

---

## 7. Non-Functional Requirements

* **Reliability**

  * Bot should automatically restart on crash or server reboot (via pm2/systemd/etc.).

* **Config via Environment Variables**

  * No hard-coded tokens or IDs.
  * Use `.env` or environment variables for:

    * `TELEGRAM_BOT_TOKEN`
    * `TELEGRAM_CHANNEL_ID`

* **Logs**

  * Basic logging of:

    * Errors/exceptions
    * Message received / posted events (without exposing sensitive user info in logs if not necessary).

---

## 8. Future / Optional Features (Not Required for v1)

These are **nice-to-have** ideas for later:

* Simple moderation:

  * Queue messages for approval before posting.
  * Admin interface via a private group/chat.
* Anti-spam:

  * Rate limiting per user (e.g., max X messages per minute).
* Content filtering:

  * Block certain words/phrases.
* Commands for admins:

  * `/stats` (number of messages posted, etc.)
  * `/ban`, `/mute` (if we introduce user IDs in mod layer).

---

## 9. What We Expect From the Implementation

* A small, clean project that:

  * Can be started via `python bot.py` or `node bot.js`.
  * Includes basic instructions in `README.md`:

    * How to install dependencies
    * How to set environment variables
    * How to run the bot
    * How to run it with pm2/systemd for 24/7 uptime.

* The final result should:

  * Be easy to deploy on a fresh Ubuntu VPS.
  * Work reliably as an anonymous message forwarder bot for a Telegram channel.
