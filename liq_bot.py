import os
import telebot

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ TOKEN not set!")
    exit(1)

print("✅ TOKEN is set! Starting bot...")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'test'])
def start(message):
    bot.reply_to(message, "✅ Bot is working! TOKEN is correct.")

print("✅ Bot running successfully")
bot.infinity_polling()
