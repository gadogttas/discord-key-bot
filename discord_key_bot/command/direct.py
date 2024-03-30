from typing import Dict, List

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from discord_key_bot.db import search
from sqlalchemy.orm import sessionmaker, Session

from discord_key_bot.common import util
from discord_key_bot.db.models import Game, Key, Member
from discord_key_bot.common.util import GamePlatformCount
from discord_key_bot.platform import (
    infer_platform,
    PlatformNotFound,
    all_platforms,
    Platform,
)
from discord_key_bot.common.colours import Colours


class DirectCommands(commands.Cog):
    """Run these commands in private messages to the bot"""

    def __init__(self, bot: Bot, db_session_maker: sessionmaker):
        self.bot: Bot = bot
        self.db_sessionmaker: sessionmaker = db_session_maker

    @commands.command()
    async def add(self, ctx: commands.Context, key: str, *game_name: str) -> None:
        """Add a key"""
        session: Session = self.db_sessionmaker()

        pretty_name: str = " ".join(game_name)

        if not pretty_name:
            await util.send_error_message(ctx, "No game name provided!")
            return

        game: Game = Game.get(session, pretty_name)

        try:
            platform: Platform = infer_platform(key)
        except PlatformNotFound:
            await ctx.send(embed=util.embed("Unrecognized key format!", Colours.RED))
            return

        if ctx.guild:
            try:
                await ctx.message.delete()
            except Exception:
                pass
            await ctx.author.send(
                embed=util.embed(
                    "You should really do this here, so it's only the bot giving away keys.",
                    colour=Colours.LUMINOUS_VIVID_PINK,
                )
            )

        if search.key_exists(session, key):
            await ctx.send(
                embed=util.embed(
                    f"Key already exists!",
                    Colours.GOLD,
                )
            )
            return

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        game.keys.append(
            Key(platform=platform.search_name, key=key, creator=member, game=game)
        )

        session.commit()

        await ctx.author.send(
            embed=util.embed(
                f'Key for "{game.pretty_name}" added. Thanks {ctx.author.name}!',
                Colours.GREEN,
                title=f"{platform.name} Key Added",
            )
        )

    @commands.command()
    async def remove(
        self, ctx: commands.Context, platform: str, *game_name: str
    ) -> None:
        """Remove a key and send to you in a PM"""

        platform_lower: str = platform.lower()

        if platform_lower not in all_platforms.keys():
            await ctx.send(
                embed=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search Error",
                )
            )
            return

        search_args: str = util.get_search_arguments("_".join(game_name))

        if not search_args:
            await util.send_error_message(ctx, "No game name provided!")
            return

        session: Session = self.db_sessionmaker()

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        game_keys: Dict[str, List[Key]] = search.find_game_keys_for_user(
            session, member, platform, search_args
        )
        if not game_keys:
            await ctx.send(embed=util.embed("Game not found"))
            return

        key: Key = game_keys[platform_lower][0]
        game: Game = key.game

        msg: Embed = util.embed(
            f"Please find your key below", title="Key removed!", colour=Colours.GREEN
        )

        msg.add_field(name=game.pretty_name, value=key.key)

        session.delete(key)
        session.commit()

        if not game.keys:
            session.delete(game)

        session.commit()

        await ctx.author.send(embed=msg)

    @commands.command()
    async def mykeys(self, ctx: commands.Context, page: int = 1) -> None:
        """Browse your own keys"""
        if ctx.guild:
            await ctx.author.send(
                embed=util.embed(f"This command needs to be sent in a direct message")
            )
            return

        session: Session = self.db_sessionmaker()
        member = Member.get(session, ctx.author.id, ctx.author.name)

        per_page: int = 15
        offset: int = (page - 1) * per_page

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session, page=page, per_page=per_page, member_id=member.id
        )

        total: int = search.count_games(session=session, member_id=member.id)
        first, last = util.get_page_bounds(page, per_page, total)

        msg: Embed = util.embed(f"Showing {first} to {last} of {total}")
        util.add_games_to_message(msg, games)

        await ctx.send(embed=msg)
