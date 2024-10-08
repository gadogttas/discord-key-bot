import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Bot, CommandError
from sqlalchemy.orm import sessionmaker

from discord_key_bot.command import guild, direct
from discord_key_bot.common import util


async def new(
    db_session_maker: sessionmaker,
    bot_channel_id: int,
    command_prefix: str,
    wait_time: datetime.timedelta,
    page_size: int,
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

        message: str
        if isinstance(error, commands.CommandNotFound):
            message = f"**Invalid command. Try using** `{command_prefix}help` **to figure out commands.**"
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"**Please pass in all requirements. Use** `{command_prefix}help {ctx.invoked_with}` **to see requirements.**"
        else:
            return

        if isinstance(ctx.cog, direct.DirectCommands):
            if bool(ctx.guild):
                await ctx.message.delete()

        await util.send_message(
            ctx=ctx,
            msg=message,
        )

    @bot.check
    async def is_bot_channel(ctx: commands.Context) -> bool:
        return not bool(ctx.guild) or ctx.channel.id == bot_channel_id

    # register cogs
    await bot.add_cog(guild.GuildCommands(bot, db_session_maker, wait_time, page_size))
    await bot.add_cog(direct.DirectCommands(bot, db_session_maker, page_size))

    discord.utils.setup_logging()

    return bot
