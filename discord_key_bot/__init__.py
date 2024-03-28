import datetime

from discord.ext import commands
from discord.ext.commands import CommandError, Bot

from .command import direct, guild


def new(bot_channel_id: str, command_prefix: str, wait_time: datetime.timedelta) -> Bot:
    bot = commands.Bot(command_prefix=command_prefix)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: CommandError):
        if bot_channel_id and str(ctx.channel.id) != bot_channel_id:
            return  # We don't care about the wrong commands in other channels
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                f"**Invalid command. Try using** `{command_prefix}help` **to figure out commands.**"
            )
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"**Please pass in all requirements. Use** `{command_prefix}help {ctx.invoked_with}` **to see requirements.**"
            )

    bot.add_cog(guild.GuildCommands(bot, bot_channel_id, wait_time))
    bot.add_cog(direct.DirectCommands(bot))

    return bot
