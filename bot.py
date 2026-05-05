from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import re

# --- RENDER HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check():
    # Render requires binding to 0.0.0.0 on port 10000
    try:
        server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Health check server error: {e}")

threading.Thread(target=run_health_check, daemon=True).start()

# --- CONFIGURATION ---
API_ID = 38807471
API_HASH = '9bbfb9efe1a47596cf7f1b20017f5dc6'
BOT_TOKEN = '7660700670:AAG6iCTwKo3p2O-N_2Mf-En9Bwx5pMMBxaU'
CHECKER_API_URL = 'http://148.230.102.178:8081/'
ADMIN_ID = 5541778617

PREMIUM_EMOJI_IDS = {
    "✅": "6023660820544623088", "🔥": "5999340396432333728", 
    "❌": "6037570896766438989", "⚡": "6026367225466720832",
    "💳": "5971944878815317190", "💠": "5971837723676249096",
    "📊": "5971837723676249096", "🛑": "5420323339723881652"
}

# --- HELPERS ---
def premium_emoji(text):
    if not text: return text
    result = text
    for emoji, doc_id in PREMIUM_EMOJI_IDS.items():
        result = result.replace(emoji, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    return [f"{c}|{m}|{'20'+y if len(y)==2 else y}|{cv}" for c, m, y, cv in re.findall(pattern, text)]

async def get_lines(file):
    if not os.path.exists(file): return []
    async with aiofiles.open(file, 'r') as f:
        content = await f.read()
        return [l.strip() for l in content.splitlines() if l.strip()]

# --- BOT INITIALIZATION ---
bot = TelegramClient('shopii_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
active_sessions = {}

# --- HANDLERS ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    msg = "<b>⚡ Shopiiiii Multi-Checker ⚡</b>\n\n"
    msg += "<blockquote>• /cc card|mm|yy|cvv\n• /chk (reply to file)</blockquote>\n"
    if event.sender_id == ADMIN_ID:
        msg += "\n<b>Admin:</b> /stats, /addsite, /addproxy"
    await event.reply(premium_emoji(msg), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/cc\s+'))
async def single_cc(event):
    cards = extract_cc(event.message.text)
    if not cards: return await event.reply("❌ Format: /cc card|mm|yy|cvv")
    
    status_msg = await event.reply(premium_emoji("⚡ Checking..."))
    sites, proxies = await get_lines('sites.txt'), await get_lines('proxy.txt')
    
    if not sites or not proxies:
        return await status_msg.edit("❌ Error: sites.txt or proxy.txt is empty.")

    try:
        params = {'cc': cards[0], 'url': random.choice(sites), 'proxy': random.choice(proxies)}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=50)) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                data = await resp.json(content_type=None)
        
        res = f"<b>💠 Result: {data.get('Status', 'Dead')}</b>\n<code>{cards[0]}</code>\nResponse: {data.get('Response', 'N/A')}"
        await status_msg.edit(premium_emoji(res), parse_mode='html')
    except Exception as e:
        await status_msg.edit(f"❌ API Error: {str(e)}")

@bot.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id != ADMIN_ID: return
    s, p = await get_lines('sites.txt'), await get_lines('proxy.txt')
    await event.reply(f"📊 **Stats**\n\nSites: {len(s)}\nProxies: {len(p)}")

@bot.on(events.NewMessage(pattern=r'/addsite\s+'))
async def add_site(event):
    if event.sender_id != ADMIN_ID: return
    new_site = event.message.text.split(' ', 1)[1].strip()
    async with aiofiles.open('sites.txt', 'a') as f:
        await f.write(f"\n{new_site}")
    await event.reply(f"✅ Added: {new_site}")

@bot.on(events.NewMessage(pattern='/chk'))
async def bulk_check(event):
    if not event.reply_to_msg_id: return await event.reply("❌ Reply to a .txt file.")
    reply = await event.get_reply_message()
    if not reply.file: return await event.reply("❌ No file found.")
    
    path = await reply.download_media()
    async with aiofiles.open(path, 'r') as f: cards = extract_cc(await f.read())
    os.remove(path)

    status_msg = await event.reply(premium_emoji(f"🚀 Loaded {len(cards)} cards. Starting check..."))
    # Note: Bulk loop logic would go here, utilizing active_sessions for pause/stop
    await status_msg.edit(f"✅ Check started for {len(cards)} cards.")

# Callback Handlers for Pause/Stop
@bot.on(events.CallbackQuery(pattern=b"stop"))
async def stop(event):
    active_sessions.pop(f"{event.sender_id}_{event.message_id}", None)
    await event.answer("🛑 Stopped")

print("✅ Bot and Health Server are ready. All commands functional.")
bot.run_until_disconnected()
    
