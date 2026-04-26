import telebot
import os
import requests
from datetime import datetime

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ TOKEN not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

def get_heatmap_coins():
    try:
        url = "https://open-api-v4.coinglass.com/api/futures/liquidation/coin-list"
        response = requests.get(url, timeout=15)
        data = response.json().get('data', [])[:10]

        price_url = "https://api.coingecko.com/api/v3/coins/markets"
        price_params = {"vs_currency": "usd", "order": "volume_desc", "per_page": 50, "page": 1}
        price_data = requests.get(price_url, params=price_params, timeout=12).json()
        price_map = {coin['symbol'].upper(): coin['current_price'] for coin in price_data}

        now = datetime.now().strftime("%d %B %Y, %H:%M IST")
        msg = f"🔥 **15-Min Coinglass Heatmap Alert** - {now}\n\n"

        for i, coin in enumerate(data, 1):
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

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "👋 Send /liq for Coinglass Heatmap Alert")

@bot.message_handler(commands=['liq', 'heatmap'])
def send_liq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    text = get_heatmap_coins()
    bot.reply_to(message, text, parse_mode='Markdown')

print("✅ Bot running - Clean version")
bot.infinity_polling()
