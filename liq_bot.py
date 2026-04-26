import os
import time
import requests
import telebot
import schedule
import threading
from datetime import datetime

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CG_API_KEY = os.getenv("COINGLASS_API_KEY")

if not TOKEN:
    print("❌ TOKEN not set!"); exit(1)
if not CHAT_ID:
    print("❌ CHAT_ID not set!"); exit(1)
if not CG_API_KEY:
    print("❌ COINGLASS_API_KEY not set!"); exit(1)

print("✅ All env vars set! Starting bot...")

bot = telebot.TeleBot(TOKEN)
CG_BASE = "https://open-api-v4.coinglass.com"
CG_HEADERS = {"CG-API-KEY": CG_API_KEY, "accept": "application/json"}

# ===== FETCH DATA (1 call gives ALL coins!) =====
def fetch_all_coins():
    """Single API call returns full market data for all coins"""
    try:
        url = f"{CG_BASE}/api/futures/coins-markets"
        r = requests.get(url, headers=CG_HEADERS, timeout=20)
        print(f"  Coinglass API status: {r.status_code}")
        if r.status_code != 200:
            print(f"  Response: {r.text[:300]}")
            return None
        data = r.json()
        if data.get("code") != "0":
            print(f"  API error: {data.get('msg', 'unknown')}")
            return None
        return data.get("data", [])
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return None

# ===== SIGNAL LOGIC =====
def analyze_coin(coin):
    """Returns analysis dict from coin data"""
    try:
        symbol = coin.get("symbol", "?")
        price = float(coin.get("current_price") or 0)
        if price <= 0:
            return None
        
        oi_usd = float(coin.get("open_interest_usd") or 0)
        oi_change_24h = float(coin.get("open_interest_change_percent_24h") or 0)
        change_15m = float(coin.get("price_change_percent_15m") or 0)
        change_1h = float(coin.get("price_change_percent_1h") or 0)
        change_24h = float(coin.get("price_change_percent_24h") or 0)
        funding = float(coin.get("avg_funding_rate_by_oi") or 0) * 100  # to %
        long_liq = float(coin.get("long_liquidation_usd_24h") or 0)
        short_liq = float(coin.get("short_liquidation_usd_24h") or 0)
        market_cap = float(coin.get("market_cap_usd") or 0)
        
        # Decide LONG / SHORT using multi-signal score
        score = 0
        if change_15m > 0.3: score += 1
        if change_15m < -0.3: score -= 1
        if change_1h > 1: score += 1
        if change_1h < -1: score -= 1
        if oi_change_24h > 2: score += 1
        if oi_change_24h < -2: score -= 1
        # Contrarian funding rate signal
        if funding > 0.05: score -= 1   # high funding = longs overheated
        if funding < -0.02: score += 1  # negative funding = shorts paying
        # More longs got liquidated = potential bounce up
        if long_liq > short_liq * 1.5: score += 1
        if short_liq > long_liq * 1.5: score -= 1
        
        direction = "LONG" if score >= 0 else "SHORT"
        abs_score = abs(score)
        if abs_score >= 4: strength = "Very Strong"
        elif abs_score >= 2: strength = "Strong"
        else: strength = "Moderate"
        
        # Entry / SL / TP
        if direction == "LONG":
            entry = price
            sl = price * 0.985    # -1.5%
            tp = price * 1.12     # +12%
            emoji = "🟢"
        else:
            entry = price
            sl = price * 1.015    # +1.5%
            tp = price * 0.88     # -12%
            emoji = "🔴"
        
        return {
            "symbol": symbol, "price": price, "direction": direction,
            "emoji": emoji, "strength": strength,
            "entry": entry, "sl": sl, "tp": tp,
            "oi_usd": oi_usd, "oi_change": oi_change_24h,
            "change_15m": change_15m, "change_1h": change_1h, "change_24h": change_24h,
            "funding": funding, "long_liq": long_liq, "short_liq": short_liq,
            "market_cap": market_cap, "total_liq": long_liq + short_liq,
        }
    except Exception as e:
        print(f"⚠️ Analyze error: {e}")
        return None

# ===== FORMATTING =====
def fmt_price(p):
    if p >= 1000: return f"{p:,.2f}"
    if p >= 1: return f"{p:,.4f}"
    return f"{p:.6f}"

def fmt_money(n):
    if n >= 1e9: return f"${n/1e9:.2f}B"
    if n >= 1e6: return f"${n/1e6:.2f}M"
    if n >= 1e3: return f"${n/1e3:.1f}K"
    return f"${n:,.0f}"

# ===== BUILD ALERT =====
def build_alert():
    coins_raw = fetch_all_coins()
    if not coins_raw:
        return "⚠️ Could not fetch Coinglass data. Check API key / rate limit."
    
    # Top 15 by market cap
    coins_sorted = sorted(coins_raw, key=lambda c: float(c.get("market_cap_usd") or 0), reverse=True)
    top15 = coins_sorted[:15]
    
    now = datetime.now().strftime("%d %b %Y, %H:%M IST")
    msg = f"<b>🔥 15-Min Coinglass Heatmap Alert - {now}</b>\n\n"
    
    success = 0
    for i, coin in enumerate(top15, 1):
        d = analyze_coin(coin)
        if not d:
            continue
        success += 1
        
        msg += f"<b>{i}. {d['emoji']} {d['symbol']}</b> (~${fmt_price(d['price'])})\n"
        msg += f"  24h Liq: {fmt_money(d['total_liq'])} (L:{fmt_money(d['long_liq'])} | S:{fmt_money(d['short_liq'])})\n"
        msg += f"  <b>MAX PROFIT {d['direction']}</b> ({d['strength']})\n"
        msg += f"  OI: {fmt_money(d['oi_usd'])} | OI 24h: {d['oi_change']:+.2f}%\n"
        msg += f"  Δ 15m: {d['change_15m']:+.2f}% | 1h: {d['change_1h']:+.2f}% | 24h: {d['change_24h']:+.2f}%\n"
        msg += f"  Funding: {d['funding']:+.4f}%\n"
        msg += f"  Entry: ${fmt_price(d['entry'])} | SL: ${fmt_price(d['sl'])} (1.5%)\n"
        msg += f"  TP: ${fmt_price(d['tp'])} → <b>MAX PROFIT: +12%</b>\n\n"
    
    msg += f"<i>✅ {success}/15 coins | ⚠️ Educational only. DYOR.</i>"
    return msg

# ===== SEND =====
def send_alert():
    print(f"\n📤 Building alert at {datetime.now().strftime('%H:%M:%S')}")
    try:
        msg = build_alert()
        # Telegram 4096 char limit - split if needed
        if len(msg) > 4000:
            chunks = []
            current = ""
            for block in msg.split("\n\n"):
                if len(current) + len(block) + 2 > 4000:
                    chunks.append(current)
                    current = block + "\n\n"
                else:
                    current += block + "\n\n"
            if current:
                chunks.append(current)
            for c in chunks:
                bot.send_message(CHAT_ID, c, parse_mode="HTML")
                time.sleep(1)
        else:
            bot.send_message(CHAT_ID, msg, parse_mode="HTML")
        print("✅ Alert sent!")
    except Exception as e:
        print(f"❌ Send error: {e}")

# ===== COMMANDS =====
@bot.message_handler(commands=['start', 'test'])
def start_cmd(m):
    bot.reply_to(m, "✅ Bot running! Real Coinglass alerts every 15 min.\n\n/now - send alert now\n/chatid - your chat ID")

@bot.message_handler(commands=['now'])
def now_cmd(m):
    bot.reply_to(m, "📤 Building alert...")
    send_alert()

@bot.message_handler(commands=['chatid'])
def chatid_cmd(m):
    bot.reply_to(m, f"Chat ID: <code>{m.chat.id}</code>", parse_mode="HTML")

# ===== SCHEDULER =====
def run_scheduler():
    schedule.every(15).minutes.do(send_alert)
    print("⏰ Scheduler: alerts every 15 min")
    while True:
        schedule.run_pending()
        time.sleep(20)

# ===== START =====
print("🔧 Removing webhook...")
bot.remove_webhook()
time.sleep(2)

print("📤 Sending startup alert...")
send_alert()

print("🚀 Starting scheduler thread...")
threading.Thread(target=run_scheduler, daemon=True).start()

print("👂 Polling Telegram...")
bot.infinity_polling(timeout=20, long_polling_timeout=10)
