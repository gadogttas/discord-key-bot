import os
from datetime import timedelta

from dotenv import load_dotenv

import discord_key_bot

load_dotenv()

COMMAND_PREFIX = os.environ.get("BANG", "!")
WAIT_TIME = timedelta(seconds=int(os.environ.get("WAIT_TIME", 86400)))
BOT_CHANNEL_ID = os.environ.get("BOT_CHANNEL_ID")
TOKEN = os.environ["TOKEN"]

bot = discord_key_bot.new(
    bot_channel_id=BOT_CHANNEL_ID, wait_time=WAIT_TIME, command_prefix=COMMAND_PREFIX
)

bot.run(TOKEN)
