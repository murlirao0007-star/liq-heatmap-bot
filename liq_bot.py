import telebot
import os
import time
import threading
from datetime import datetime
import schedule
import requests

TOKEN = os.getenv("TOKEN")
COINGLASS_KEY = os.getenv("COINGLASS_API_KEY")

if not TOKEN:
    print("❌ TOKEN not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

YOUR_CHAT_ID = 7219470795   # ← CHANGE THIS TO YOUR REAL CHAT ID

def get_heatmap_coins():
    try:
        # Coinglass
        url = "https://open-api-v4.coinglass.com/api/futures/liquidation/coin-list"
        headers = {"cg-api-key": COINGLASS_KEY} if COINGLASS_KEY else {}
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json().get('data', [])[:12]

        # Prices
        price_url = "https://api.coingecko.com/api/v3/coins/markets"
        price_params = {"vs_currency": "usd", "order": "volume_desc", "per_page": 50, "page": 1}
        price_data = requests.get(price_url, params=price_params, timeout=12).json()
        price_map = {coin['symbol'].upper(): coin['current_price'] for coin in price_data}

        now = datetime.now().strftime("%d %B %Y, %H:%M IST")
        msg = f"🔥 **15-Min Coinglass Heatmap Alert** - {now}\n\n"

        for i, coin in enumerate(data[:10], 1):
            symbol = coin.get('symbol', 'N/A')
            price = price_map.get(symbol, 0)
            long_liq = coin.get('long_liquidation_usd_24h', 0)
            short_liq = coin.get('short_liquidation_usd_24h', 0)
            total_liq = long_liq + short_liq

            entry = price
            sl = round(price * 0.92, 4) if price else 0
            tp = round(price * 1.18, 4) if price else 0

            msg += f"{i}. **{symbol}** (~${price:,.4f})\n"
            msg += f"   24h Liq: ${total_liq:,.0f} (L:${long_liq:,.0f} | S:${short_liq:,.0f})\n"
            msg += f"   Entry: ~${entry:,.4f} | SL: ~${sl:,.4f} | TP: ~${tp:,.4f}\n\n"

        msg += "⚠️ Only Coinglass Heatmap coins\n"
        msg += "Live: https://www.coinglass.com/pro/futures/LiquidationHeatMap"
        return msg

    except Exception as e:
        return f"❌ Error: {e}"

def send_alert():
    text = get_heatmap_coins()
    bot.send_message(YOUR_CHAT_ID, text, parse_mode='Markdown')

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "👋 /liq = Coinglass Heatmap Alert\nAlerts every 15 min + 8 PM IST daily.")

@bot.message_handler(commands=['liq', 'heatmap'])
def send_liq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    text = get_heatmap_coins()
    bot.reply_to(message, text, parse_mode='Markdown')

schedule.every(15).minutes.do(send_alert)
schedule.every().day.at("20:00").do(send_alert)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler, daemon=True).start()

print("✅ Bot running - Coinglass Heatmap only")
bot.infinity_polling()
