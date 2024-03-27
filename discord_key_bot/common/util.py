import discord

from discord_key_bot.common.colours import Colours


async def validate_search_args(search_args, ctx):
    if not search_args:
        await ctx.send(embed=embed("No game name provided!", Colours.RED))
        return False

    return True

def embed(text, colour=Colours.DEFAULT, title="Keybot"):
    return discord.Embed(title=title, type="rich", description=text, color=colour)
