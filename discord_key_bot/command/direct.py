import inspect
from typing import List

from discord import Embed, Forbidden, NotFound
from discord.ext import commands
from discord.ext.commands import Bot

from discord_key_bot.db import search
from sqlalchemy.orm import sessionmaker, Session

from discord_key_bot.common import util
from discord_key_bot.db.models import Game, Key, Member
from discord_key_bot.common.util import GamePlatformCount, send_message, get_page_header_text
from discord_key_bot.db.queries import SortOrder
from discord_key_bot.platform import (
    all_platforms,
    Platform,
)
from discord_key_bot.common.colours import Colours


class DirectCommands(commands.Cog, name='Direct Message Commands'):
    """Run these commands in private messages to the bot"""

    def __init__(self, bot: Bot, db_session_maker: sessionmaker, page_size: int):
        self.bot: Bot = bot
        self.db_sessionmaker: sessionmaker = db_session_maker
        self.page_size: int = page_size

    @commands.command()
    async def add(
        self,
        ctx: commands.Context,
        platform_name: str = commands.Parameter(
            name="platform_name",
            displayed_name="Platform Name",
            description=f"The platform this key is for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        key: str = commands.Parameter(
            name="key",
            displayed_name="Key",
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

        if ctx.guild:
            try:
                await ctx.message.delete()
            except (Forbidden, NotFound):
                pass
            await ctx.author.send(
                embed=util.embed(
                    "You should really do this here, so it's only the bot giving away keys.",
                    colour=Colours.LUMINOUS_VIVID_PINK,
                )
            )

        try:
            platform: Platform = all_platforms[platform_name.lower()]
        except KeyError:
            await ctx.author.send(
                embed=util.embed("Invalid platform name.", Colours.RED),
            )
            return

        if not platform.is_valid_key(key):
            await ctx.author.send(
                embed=util.embed("This key is not valid for this platform.", Colours.RED),
            )
            return

        if search.key_exists(session, key):
            await send_message(
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
            await send_message(
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

        game_keys: List[Key] = search.find_game_keys_for_user(
            session, member, platform, game_name
        )
        if not game_keys:
            await send_message(ctx=ctx, msg=util.embed("Game not found"))
            return

        key: Key = game_keys[0]
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
            description=f"The page number",
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

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            page=page,
            per_page=self.page_size,
            member_id=member.id,
            sort=SortOrder.TITLE,
        )

        total: int = search.count_games(session=session, member_id=member.id)

        msg: Embed = util.build_page_message(
            title="Your Keys",
            text=get_page_header_text(page, total, self.page_size),
            games=games,
        )

        await send_message(ctx=ctx, msg=msg)
