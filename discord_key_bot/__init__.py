from discord.ext import commands

from .command import direct_commands, guild_commands


def new(bot_channel_id, command_prefix, wait_time):
    bot = commands.Bot(command_prefix=command_prefix)

    @bot.event
    async def on_command_error(ctx, error):
        if (bot_channel_id and str(ctx.channel.id) != bot_channel_id):
            return  # We don't care about the wrong commands in other channels
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"**Invalid command. Try using** `{command_prefix}help` **to figure out commands.**")
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"**Please pass in all requirements. Use** `{command_prefix}help {ctx.invoked_with}` **to see requirements.**")

    bot.add_cog(guild_commands.GuildCommands(bot, bot_channel_id, wait_time))
    bot.add_cog(direct_commands.DirectCommands(bot))

    return bot
