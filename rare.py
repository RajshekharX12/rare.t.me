import asyncio
from datetime import datetime
import os
import logging

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pyrogram import Client, filters
from tzlocal import get_localzone

# Load environment variables first
try:
    load_dotenv()
except Exception as e:
    print(f"Error loading environment variables: {e}")
    quit(0)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.ERROR)

log = logging.getLogger("PriceUpdaterBot")

# Check for required environment variables
required_env_vars = ["CHAT_ID", "MESSAGE_ID", "API_ID", "API_HASH", "BOT_TOKEN", "CMC_API_KEY"]
if not all(os.environ.get(i) for i in required_env_vars):
    log.critical("Missing some Variables! Check your ENV file..")
    log.info(f"Actual environment variables: {os.environ}")
    quit(0)

# Scheduler setup
scheduler = AsyncIOScheduler(timezone=str(get_localzone()))
scheduler.start()

# Pyrogram client setup
app = Client(
    "rare",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    bot_token=os.getenv("BOT_TOKEN"),
)

# Command handler
@app.on_message(filters.command(["start", "help", "ping"]))
async def init(client, msg):
    await msg.reply_text("Hello there, I'm alive & running!")

# Function to get Bitcoin prices
async def get_prices():
    headers = {"X-CMC_PRO_API_KEY": os.getenv("CMC_API_KEY")}
    async with aiohttp.ClientSession() as aio:
        try:
            resp = await aio.get(os.getenv("CMC_URL"), headers=headers, params=os.getenv("CMC_PARAMS"))
            if resp.status == 200:
                resp_data = await resp.json()
                price = resp_data["data"][0]["quote"]["USD"]["price"]
                timestamp = datetime.now().strftime("%F %T")
                return timestamp, round(price, 5)
        except Exception as exc:
            log.exception(exc)

# Scheduler function
async def scheduler_func():
    chat_id = os.getenv("CHAT_ID")
    if chat_id.lstrip("-").isdigit():
        chat_id = int(chat_id)

    log.info("Fetching prices...")
    price = await get_prices()
    log.info(f"Prices: {price}")

    if not isinstance(price, tuple):
        log.warning("Invalid price format.")
        return

    _time, price = price
    edit_msg = os.getenv("CHANNEL_MSG").format(str(price), _time)
    bio_msg = os.getenv("BIO_MSG").format(str(price))
    
    log.info(f"Editing message in chat {chat_id} with new prices: {edit_msg}")
    await asyncio.gather(
        app.edit_message(chat_id, int(os.getenv("MESSAGE_ID")), edit_msg),
        app.set_chat_description(chat_id, bio_msg),
        return_exceptions=True,
    )
    log.info("Message edited successfully.")

# Add job to scheduler
scheduler.add_job(
    scheduler_func,
    "interval",
    minutes=5,
    id="main_function",
    jitter=60,
)

# Run the Pyrogram client
app.run()
