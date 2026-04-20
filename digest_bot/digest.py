import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_PATH = os.getenv("DB_PATH", "../data/database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_latest_news_digest(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT summary, created_at FROM news_digests ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()

def fetch_period_stats(conn, hours=12):
    cursor = conn.cursor()
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    # PnL sum
    cursor.execute("SELECT SUM(pnl) as total_pnl, COUNT(*) as trade_count FROM trades WHERE created_at >= ?", (since,))
    stats = cursor.fetchone()
    
    # Top bet (highest PnL)
    cursor.execute("""
        SELECT p.text, a.impact_score, a.ticker, a.direction, a.reasoning, t.pnl, t.entry_price, t.exit_price
        FROM trades t
        JOIN analyses a ON t.analysis_id = a.id
        JOIN posts p ON a.post_id = p.id
        WHERE t.created_at >= ?
        ORDER BY t.pnl DESC
        LIMIT 1
    """, (since,))
    top_bet = cursor.fetchone()

    # Most active ticker
    cursor.execute("""
        SELECT ticker, COUNT(*) as count 
        FROM trades 
        WHERE created_at >= ? 
        GROUP BY ticker 
        ORDER BY count DESC 
        LIMIT 1
    """, (since,))
    top_ticker = cursor.fetchone()
    
    return stats, top_bet, top_ticker

def format_message(news, stats, top_bet, top_ticker):
    msg = "<b>🗞 Daily Trumpbot Digest</b>\n\n"
    
    if news:
        msg += f"<b>Latest News Summary:</b>\n<i>{news['summary'][:300]}...</i>\n\n"
    
    if stats and stats['trade_count'] > 0:
        pnl = stats['total_pnl'] or 0.0
        msg += f"<b>📊 Performance (Last 12h):</b>\n"
        msg += f"Trades executed: {stats['trade_count']}\n"
        msg += f"Total PnL: ${pnl:.2f} {'🟢' if pnl >= 0 else '🔴'}\n"
        if top_ticker:
            msg += f"Most active ticker: {top_ticker['ticker']} ({top_ticker['count']} trades)\n"
        msg += "\n"
    else:
        msg += "<b>📊 Performance (Last 12h):</b>\nNo trades executed in this period.\n\n"
        
    if top_bet:
        msg += "<b>🏆 Top Bet:</b>\n"
        msg += f"Post: \"{top_bet['text'][:100]}...\"\n"
        msg += f"Analysis: {top_bet['ticker']} {top_bet['direction']} (Impact: {top_bet['impact_score']}/10)\n"
        msg += f"Reason: {top_bet['reasoning']}\n"
        msg += f"Result: ${top_bet['pnl']:.2f} PnL\n"
    
    msg += f"\n<i>Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    return msg

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing. Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = get_db_connection()
    try:
        news = fetch_latest_news_digest(conn)
        stats, top_bet, top_ticker = fetch_period_stats(conn)
        
        message = format_message(news, stats, top_bet, top_ticker)
        if send_telegram_message(message):
            print("Digest sent successfully!")
        else:
            print("Failed to send digest.")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()
