import discord_key_bot.bot
import os

from datetime import timedelta
from dotenv import load_dotenv
from discord_key_bot.db import session_maker

load_dotenv()

COMMAND_PREFIX: str = os.environ.get("BANG", "!")
WAIT_TIME: timedelta = timedelta(seconds=int(os.environ.get("WAIT_TIME", 86400)))
BOT_CHANNEL_ID: int = int(os.environ.get("BOT_CHANNEL_ID"))
SQLALCHEMY_URI: str = os.environ.get("SQLALCHEMY_URI", "sqlite:///:memory:")
TOKEN: str = os.environ["TOKEN"]

bot = discord_key_bot.bot.new(
    db_session_maker=session_maker.new(SQLALCHEMY_URI),
    bot_channel_id=BOT_CHANNEL_ID,
    wait_time=WAIT_TIME,
    command_prefix=COMMAND_PREFIX,
)

bot.run(TOKEN)
