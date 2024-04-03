import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Bot, CommandError
from loguru import logger
from sqlalchemy.orm import sessionmaker

from discord_key_bot.command import guild, direct
from discord_key_bot.common.util import send_with_retry

log: logger = logger.bind(name="bot")

async def new(
    db_session_maker: sessionmaker,
    bot_channel_id: int,
    command_prefix: str,
    wait_time: datetime.timedelta,
) -> Bot:
    bot = commands.Bot(
        command_prefix=command_prefix,
        intents=discord.Intents(messages=True, message_content=True),
    )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: CommandError) -> None:
        if bot_channel_id and ctx.channel.id != bot_channel_id:
            return  # We don't care about the wrong commands in other channels
        if isinstance(error, commands.CommandNotFound):
            await send_with_retry(
                ctx=ctx,
                msg=f"**Invalid command. Try using** `{command_prefix}help` **to figure out commands.**",
            )

            return

        if isinstance(error, commands.MissingRequiredArgument):
            await send_with_retry(
                ctx=ctx,
                msg=f"**Please pass in all requirements. Use** `{command_prefix}help {ctx.invoked_with}` **to see requirements.**",
            )

            return

        log.debug(f"Unhandled command error: {error}")

    await bot.add_cog(
        guild.GuildCommands(bot, db_session_maker, bot_channel_id, wait_time)
    )
    await bot.add_cog(direct.DirectCommands(bot, db_session_maker))

    return bot
