import asyncio

from sqlalchemy.orm import sessionmaker

import discord_key_bot.bot
import os

from datetime import timedelta
from dotenv import load_dotenv

from discord_key_bot.common.constants import DEFAULT_PAGE_SIZE
from discord_key_bot.db import connection


async def main():
    load_dotenv()

    command_prefix: str = os.environ.get("BANG", "!")
    wait_time: timedelta = timedelta(seconds=int(os.environ.get("WAIT_TIME", 86400)))
    bot_channel_id: int = int(os.environ.get("BOT_CHANNEL_ID"))
    sqlalchemy_uri: str = os.environ.get("SQLALCHEMY_URI", "sqlite:///:memory:")
    token: str = os.environ["TOKEN"]
    page_size: int = int(os.environ.get("PAGE_SIZE", str(DEFAULT_PAGE_SIZE)))

    db_session_maker: sessionmaker = connection.new(sqlalchemy_uri)

    bot = await discord_key_bot.bot.new(
        db_session_maker=db_session_maker,
        bot_channel_id=bot_channel_id,
        wait_time=wait_time,
        command_prefix=command_prefix,
        page_size=page_size,
    )

    await bot.start(token)


asyncio.run(main())
