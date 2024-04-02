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


def add_games_to_message(msg: discord.Embed, games: List[GamePlatformCount]) -> None:
    for game in games:
        msg.add_field(name=game.name, value=game.platforms_string())


def get_search_name(title: str) -> str:
    return re.sub(r"\W", "_", title.lower())


async def send_with_retry(
    ctx: commands.Context, msg: typing.Union[str, discord.Embed], tries: int = RETRIES
) -> None:
    while True:
        try:
            if isinstance(msg, str):
                await ctx.send(msg)
            else:
                await ctx.send(embed=msg)
            return
        except Exception as e:
            if tries:
                tries -= 1
            else:
                raise e


def get_page_header_text(page: int, total: int, per_page: int) -> str:
    pages: int = ceil(total / per_page)

    return f"Showing page {page} of {pages} ({total} games)"
