import re
import typing
from typing import List, Tuple

import discord
from discord.ext import commands

from discord_key_bot.common.colours import Colours
from discord_key_bot.platform import Platform


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


def get_page_bounds(page: int, per_page: int, total: int) -> Tuple[int, int]:
    offset: int = (page - 1) * per_page

    first: int = min(offset + 1, total)
    last: int = min(page * per_page, total)

    return first, last


def embed(
    text: str, colour: Colours = Colours.DEFAULT, title: str = "Keybot"
) -> discord.Embed:
    return discord.Embed(title=title, type="rich", description=text, color=colour)


def add_games_to_message(msg: discord.Embed, games: List[GamePlatformCount]) -> None:
    for game in games:
        msg.add_field(name=game.name, value=game.platforms_string())


async def send_error_message(ctx: commands.Context, message: str) -> None:
    await ctx.send(embed=embed(message, Colours.RED))


def get_search_name(title: str) -> str:
    return re.sub(r"\W", "_", title.lower())
