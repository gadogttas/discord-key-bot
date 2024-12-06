import asyncio
import logging

from sqlalchemy.orm import sessionmaker

import discord_key_bot.bot
import os

from datetime import timedelta
from dotenv import load_dotenv

from discord_key_bot.common.constants import DEFAULT_PAGE_SIZE
from discord_key_bot.db import connection


async def start():
    load_dotenv()

    loglevel_str: str = os.environ.get("LOGLEVEL", "INFO")
    log_level: int = logging.getLevelName(loglevel_str)
    logging.basicConfig(level=log_level)

    logger = logging.getLogger("discord-key-bot.start")
    logger.debug(f"Log level set to {loglevel_str}")

    command_prefix: str = os.environ.get("BANG", "!")
    logger.debug(f"Command prefix: {command_prefix}")

    wait_time: timedelta = timedelta(seconds=int(os.environ.get("WAIT_TIME", 86400)))
    logger.debug(f"Claim cooldown: {wait_time}")

    bot_channel_id: int = int(os.environ.get("BOT_CHANNEL_ID"))
    logger.debug(f"Bot Channel ID: {bot_channel_id}")

    sqlalchemy_uri: str = os.environ.get("SQLALCHEMY_URI", "sqlite:///:memory:")
    logger.debug(f"Database URI: {sqlalchemy_uri}")

    page_size: int = int(os.environ.get("PAGE_SIZE", str(DEFAULT_PAGE_SIZE)))
    logger.debug(f"Page size: {page_size}")

    token: str = os.environ["TOKEN"]

    db_sessionmaker: sessionmaker = connection.new(sqlalchemy_uri)
    logger.info("Successfully initialized database connection")

    bot = await discord_key_bot.bot.new(
        db_sessionmaker=db_sessionmaker,
        bot_channel_id=bot_channel_id,
        wait_time=wait_time,
        command_prefix=command_prefix,
        page_size=page_size,
        log_level=log_level,
        log_handler=logging.StreamHandler()
    )

    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(start())
