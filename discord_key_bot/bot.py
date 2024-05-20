import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Bot, CommandError
from sqlalchemy.orm import sessionmaker

from discord_key_bot.command import guild, direct
from discord_key_bot.common.util import send_with_retry


async def new(
    db_session_maker: sessionmaker,
    bot_channel_id: int,
    command_prefix: str,
    wait_time: datetime.timedelta,
) -> Bot:
    bot = commands.Bot(
        command_prefix=command_prefix,
        intents=discord.Intents(messages=True, message_content=True, guilds=True),
        help_command=commands.DefaultHelpCommand(dm_help=False),
    )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: CommandError):
        if not await is_bot_channel(ctx):
            return

        if isinstance(error, commands.CommandNotFound):
            await send_with_retry(
                ctx=ctx,
                msg=f"**Invalid command. Try using** `{command_prefix}help` **to figure out commands.**",
            )
        if isinstance(error, commands.MissingRequiredArgument):
            await send_with_retry(
                ctx=ctx,
                msg=f"**Please pass in all requirements. Use** `{command_prefix}help {ctx.invoked_with}` **to see requirements.**",
            )

    @bot.check
    async def is_bot_channel(ctx: commands.Context) -> bool:
        return not bool(ctx.guild) or ctx.channel.id == bot_channel_id

    await bot.add_cog(
        guild.GuildCommands(bot, db_session_maker, wait_time)
    )
    await bot.add_cog(direct.DirectCommands(bot, db_session_maker))

    return bot
