import telebot
import os
from datetime import datetime

# Get token securely from Railway environment variable
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ Error: TOKEN environment variable is not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

def get_liq_message():
    now = datetime.now().strftime("%d April 2026, %H:%M IST")
    msg = f"🔥 **Top 10 Liquidation Heatmap Coins** - {now}\n\n"
    msg += "1. **HYPER** (~$0.17)\n   SL: 8-12% below | TP1: 15-25% | TP2: 35-50%+\n\n"
    msg += "2. **APE** (~$0.19)\n   SL: 8-10% below | TP1: 18-25% | TP2: 35-45%\n\n"
    msg += "3. **BNB**\n   SL: Below recent low | TP1: Next resistance\n\n"
    msg += "4. **AXS**\n   SL: 5-8% tight | TP1: 12-18%\n\n"
    msg += "5. **ORCA**\n   SL: 7-10% below | TP1: 15-22%\n\n"
    msg += "6. **BSB** (~$0.66)\n   SL: 8-12% below | TP1: 15-25% | TP2: 35-50%\n   🔥 High activity now!\n\n"
    msg += "7. **TRUMP**\n   SL: 12-15% below | TP1: 25-40%\n\n"
    msg += "8. **KAT**\n   SL: 5-8% tight | TP: 15-30%\n\n"
    msg += "9. **BTC** (~$77,650)\n   SL: $76,800 | TP1: $79,500 | TP2: $81,300\n\n"
    msg += "10. **ETH** (~$2,317)\n   SL: $2,250 | TP1: $2,400 | TP2: $2,550\n\n"
    msg += "⚠️ Heatmap changes fast. Always check live:\n"
    msg += "https://www.coinglass.com/pro/futures/LiquidationHeatMap\n"
    msg += "Risk only 1% per trade!"
    return msg

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "👋 Send /liq or /heatmap to see Top 10 liquidation heatmap coins with SL & TP.")

@bot.message_handler(commands=['liq', 'heatmap'])
def send_liq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    text = get_liq_message()
    bot.reply_to(message, text, parse_mode='Markdown')

print("✅ Bot is running... Type /liq in Telegram")
bot.infinity_polling()
