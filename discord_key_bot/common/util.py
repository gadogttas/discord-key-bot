import datetime
import re
import typing
from math import ceil
from typing import List, Tuple

import discord
from discord.ext import commands

from discord_key_bot.common.colours import Colours
from discord_key_bot.platform import Platform

RETRIES: int = 3


class PlatformCount(typing.NamedTuple):
    platform: Platform
    count: int

    def __str__(self) -> str:
        return f"{self.platform.name}: {self.count}"


class GamePlatformCount(typing.NamedTuple):
    name: str
    platforms: List[PlatformCount]

    def platforms_string(self) -> str:
        return ", ".join(str(platform) for platform in self.platforms)


def embed(
    text: str, colour: Colours = Colours.DEFAULT, title: str = "Keybot"
) -> discord.Embed:
    return discord.Embed(title=title, type="rich", description=text, color=colour)


def build_page_message(title: str, text: str, games: List[GamePlatformCount]) -> discord.Embed:
    if not games:
        return embed(text="No matching games found.", title=title)

    msg: discord.Embed = embed(title=title, text=text)
    for game in games:
        msg.add_field(name=game.name, value=game.platforms_string())

    return msg


def get_search_name(title: str) -> str:
    return re.sub(r"\W", "_", title.lower())


async def send_message(
    ctx: commands.Context, msg: typing.Union[str, discord.Embed]
) -> None:
    if is_direct_message(ctx):
        await send_direct_message(ctx, msg)
    else:
        await send_channel_message(ctx, msg)


async def send_direct_message(ctx: commands.Context, msg: typing.Union[str, discord.Embed]) -> None:
    if isinstance(msg, str):
        await ctx.author.send(msg)
    else:
        await ctx.author.send(embed=msg)


async def send_channel_message(ctx: commands.Context, msg: typing.Union[str, discord.Embed]) -> None:
    if isinstance(msg, str):
        await ctx.send(msg)
    else:
        await ctx.send(embed=msg)


def get_page_header_text(page: int, total: int, per_page: int) -> str:
    pages: int = ceil(total / per_page)

    return f"Showing page {page} of {pages} ({total} games)"


def is_direct_message(ctx: commands.Context) -> bool:
    return not ctx.guild


def pretty_timedelta(delta: datetime.timedelta) -> str:
    days: int
    hours: int
    minutes: int
    seconds: int

    seconds: int = int(delta.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    if days > 0:
        return f'{days} days {hours} hours {minutes} minutes and {seconds} seconds'
    elif hours > 0:
        return f'{hours} hours {minutes} minutes and {seconds} seconds'
    elif minutes > 0:
        return f'{minutes} minutes and {seconds} seconds'
    else:
        return f'{seconds} seconds'
