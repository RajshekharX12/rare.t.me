import asyncio
from datetime import datetime
import os
import logging

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pyrogram import Client, filters
from tzlocal import get_localzone

# strings
CHANNEL_MSG = """Live Bitcoin Prices: \n\n• USDT: ${}\n\n• Updated on {}."""
BIO_MSG = """Bitcoin's Prices are ${}"""

# logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.ERROR)

log = logging.getLogger("PriceUpdaterBot")

# env
load_dotenv()

if not all(os.environ.get(i) for i in ("CHAT_ID", "MESSAGE_ID", "API_KEY", "API_ID", "API_HASH", "BOT_TOKEN")):
    log.critical("Missing some Variables! Check your ENV file..")
    quit(0)

# scheduler object
scheduler = AsyncIOScheduler(timezone=str(get_localzone()))
scheduler.start()

# pyrogram client
app = Client(
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN"),
    in_memory=True,
)

@app.on_message(filters.command(["start", "help", "ping"]))
async def init(client, msg):
    await msg.reply_text("Hello there, I'm alive & running!")

async def get_prices():
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}

    async with aiohttp.ClientSession() as aio:
        try:
            resp = await aio.get(url, params=params)
            if resp.status == 200:
                resp_data = await resp.json()
                price = float(resp_data["price"])
                timestamp = datetime.now().strftime("%F %T")
                return timestamp, round(price, 5)
        except Exception as exc:
            log.exception(exc)

async def scheduler_func():
    chat_id = os.getenv("CHAT_ID")
    if chat_id.lstrip("-").isdigit():
        chat_id = int(chat_id)

    price = await get_prices()
    if not isinstance(price, tuple):
        return

    _time, price = price
    edit_msg = CHANNEL_MSG.format(str(price), _time)
    bio_msg = BIO_MSG.format(str(price))
    
    await asyncio.gather(
        app.edit_message(chat_id, int(os.getenv("MESSAGE_ID")), edit_msg),
        app.set_chat_description(chat_id, bio_msg),
        return_exceptions=True,
    )

scheduler.add_job(
    scheduler_func,
    "interval",
    minutes=5,
    id="main_function",
    jitter=60,
)

app.run()
