import datetime
import logging

import discord
from discord.ext import commands
from discord.ext.commands import Bot, CommandError
from sqlalchemy.orm import sessionmaker

from discord_key_bot.command import guild, direct, admin
from discord_key_bot.common import util


async def new(
    db_sessionmaker: sessionmaker,
    bot_channel_id: int,
    command_prefix: str,
    wait_time: datetime.timedelta,
    page_size: int,
    expiration_waiver_period: datetime.timedelta,
    log_level: int = logging.INFO,
    log_handler: logging.Handler = logging.StreamHandler(),
) -> Bot:
    discord.utils.setup_logging(handler=log_handler, level=log_level)
    logger = logging.getLogger("discord_key_bot.bot")

    bot = commands.Bot(
        command_prefix=command_prefix,
        intents=discord.Intents(messages=True, message_content=True, guilds=True),
        help_command=commands.DefaultHelpCommand(dm_help=False),
    )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: CommandError):
        if not await is_bot_channel(ctx):
            return

        message: str = ""
        if isinstance(error, commands.CommandNotFound):
            message = f"**Invalid command. Try using** `{command_prefix}help` **to figure out commands.**"
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"**Please pass in all requirements. Use** `{command_prefix}help {ctx.invoked_with}` **to see requirements.**"
        else:
            logger.critical(f"{type(ctx.cog).__name__}.{ctx.invoked_with}: {error}")

        if isinstance(ctx.cog, direct.DirectCommands) and bool(ctx.guild):
            await ctx.message.delete()

        if message:
            await util.send_message(
                ctx=ctx,
                msg=message,
            )

    @bot.check
    async def is_bot_channel(ctx: commands.Context) -> bool:
        return not bool(ctx.guild) or ctx.channel.id == bot_channel_id

    # register cogs
    await bot.add_cog(guild.GuildCommands(bot, db_sessionmaker, wait_time, page_size, expiration_waiver_period))
    await bot.add_cog(direct.DirectCommands(bot, db_sessionmaker, page_size))
    await bot.add_cog(admin.AdminCommands(bot, db_sessionmaker))

    return bot
