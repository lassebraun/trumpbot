# Trumpbot Daily Digest Bot

This standalone bot sends a 12-hour summary of Trumpbot's activities to your Telegram.

## Features
- Latest news digest summary.
- Total PnL for the last 12 hours.
- Top bet of the period (Post + Analysis + Result).
- HTML-formatted Telegram messages.

## Setup Instructions

1. **Create a Telegram Bot:**
   - Message `@BotFather` on Telegram.
   - Use `/newbot` to create a bot and get your **API Token**.
   - Start a chat with your bot or add it to a group.
   - Use `@userinfobot` or a similar bot to find your **Chat ID**.

2. **Configure Environment:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env .env
     ```
   - Edit `.env` and fill in `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.

3. **Install Dependencies:**
   - It's recommended to use a virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     ```

4. **Test the Script:**
   ```bash
   python digest.py
   ```

5. **Schedule with Cron:**
   - Open your crontab:
     ```bash
     crontab -e
     ```
   - Add the following line to run every 12 hours (e.g., 00:00 and 12:00):
     ```bash
     0 */12 * * * cd /path/to/trumpbot/digest_bot && /path/to/trumpbot/digest_bot/venv/bin/python digest.py >> digest.log 2>&1
     ```

## Database Dependency
This script reads directly from the `database.db` file located in the `data/` folder of the main project. Ensure the `DB_PATH` in `.env` correctly points to it.
