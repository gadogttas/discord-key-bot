import inspect
from typing import Dict, List

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from discord_key_bot.db import search
from sqlalchemy.orm import sessionmaker, Session

from discord_key_bot.common import util
from discord_key_bot.db.models import Game, Key, Member
from discord_key_bot.common.util import GamePlatformCount, send_with_retry
from discord_key_bot.db.queries import SortOrder
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
    async def add(
        self,
        ctx: commands.Context,
        key: str = commands.Parameter(
            name="key",
            description="The key you wish to add",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        *,
        game_name: str = commands.Parameter(
            name="game_name",
            displayed_name="Game Name",
            description="The name of the game you wish to add a key for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
    ) -> None:
        """Add a key"""
        session: Session = self.db_sessionmaker()

        game: Game = Game.get(session, game_name)

        try:
            platform: Platform = infer_platform(key)
        except PlatformNotFound:
            await send_with_retry(
                ctx=ctx,
                msg=util.embed("Unrecognized key format!", Colours.RED),
            )
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
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(f"Key already exists!", Colours.GOLD),
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
        self,
        ctx: commands.Context,
        platform: str = commands.Parameter(
            name="platform",
            displayed_name="Platform",
            description="The platform of the game you wish to remove",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        *,
        game_name: str = commands.Parameter(
            name="game_name",
            displayed_name="Game Name",
            description="The name of the game you wish to remove",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
    ) -> None:
        """Remove a key and send to you in a PM"""

        platform_lower: str = platform.lower()

        if platform_lower not in all_platforms.keys():
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search Error",
                ),
            )
            return

        session: Session = self.db_sessionmaker()

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        game_keys: Dict[str, List[Key]] = search.find_game_keys_for_user(
            session, member, platform, game_name
        )
        if not game_keys:
            await send_with_retry(ctx=ctx, msg=util.embed("Game not found"))
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
    async def mykeys(
        self,
        ctx: commands.Context,
        page: int = commands.Parameter(
            name="page",
            displayed_name="Page Number",
            description="The page number (15 games per page)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
            default=1,
        ),
    ) -> None:
        """Browse your own keys"""
        if ctx.guild:
            await ctx.author.send(
                embed=util.embed(f"This command needs to be sent in a direct message")
            )
            return

        session: Session = self.db_sessionmaker()
        member = Member.get(session, ctx.author.id, ctx.author.name)

        per_page: int = 15

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            page=page,
            per_page=per_page,
            member_id=member.id,
            sort=SortOrder.TITLE,
        )

        total: int = search.count_games(session=session, member_id=member.id)
        first, last = util.get_page_bounds(page, per_page, total)

        msg: Embed = util.embed(f"Showing {first} to {last} of {total}")
        util.add_games_to_message(msg, games)

        await send_with_retry(ctx=ctx, msg=msg)
