import re

import discord
from discord.ext import commands

from discord_key_bot.common.colours import Colours


async def send_error_message(ctx: commands.Context, message: str) -> None:
    await ctx.send(embed=embed(message, Colours.RED))


def embed(
    text: str, colour: Colours = Colours.DEFAULT, title: str = "Keybot"
) -> discord.Embed:
    return discord.Embed(title=title, type="rich", description=text, color=colour)


def get_search_arguments(pretty_name: str) -> str:
    name = re.sub(r"\W", "_", pretty_name.lower())
    return name
