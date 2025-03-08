import inspect
import datetime
import logging
from typing import List

from discord import Embed, Forbidden, NotFound
from discord.ext import commands
from discord.ext.commands import Bot
from reactionmenu import ViewMenu

from discord_key_bot.db import search
from sqlalchemy.orm import sessionmaker

from discord_key_bot.common import util
from discord_key_bot.db.models import Game, Key, Member
from discord_key_bot.common.util import GameKeyCount, send_message, get_page_header_text
from discord_key_bot.db.queries import SortOrder
from discord_key_bot.platform import Platform, get_platform
from discord_key_bot.common.colours import Colours


class DirectCommands(commands.Cog, name='Direct Message Commands'):
    """Run these commands in private messages to the bot"""

    def __init__(self, bot: Bot, db_sessionmaker: sessionmaker, page_size: int):
        self.bot: Bot = bot
        self.db_sessionmaker: sessionmaker = db_sessionmaker
        self.page_size: int = page_size
        self.logger = logging.getLogger(__name__)

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

        if ctx.guild:
            try:
                await ctx.message.delete()
            except (Forbidden, NotFound):
                self.logger.warning("Failed to clean up improper guild message", exc_info=True)
            await ctx.author.send(
                embed=util.embed(
                    "You should really do this here, so it's only the bot giving away keys.",
                    colour=Colours.LUMINOUS_VIVID_PINK,
                )
            )

        with self.db_sessionmaker() as session:
            game: Game = Game.get(session, game_name)

            try:
                platform: Platform = get_platform(platform_name)
            except ValueError:
                await ctx.author.send(
                    embed=util.embed(f'"{platform_name}" is not valid platform', Colours.RED),
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
        platform_name: str = commands.Parameter(
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

        try:
            platform: Platform = get_platform(platform_name)
        except ValueError:
            await send_message(
                ctx=ctx,
                msg=util.embed(
                    f'"{platform_name}" is not valid platform',
                    colour=Colours.RED,
                    title="Search Error",
                ),
            )
            return

        with self.db_sessionmaker() as session:
            member: Member = Member.get(session, ctx.author.id, ctx.author.name)

            game: Game = search.get_game(session=session, game_name=game_name, member_id=member.id)
            if not game:
                await send_message(ctx=ctx, msg=util.embed("Game not found"))
                return

            key: Key = game.find_key_by_platform(platform)
            if not key:
                await send_message(ctx=ctx, msg=util.embed("No keys found for this platform"))
                return

            msg: Embed = util.embed(
                f"Please find your key below", title="Key removed!", colour=Colours.GREEN
            )

            msg.add_field(name=game.pretty_name, value=key.key)

            session.delete(key)
            session.refresh(game)
            session.flush()

            if not game.keys:
                session.delete(game)

            session.commit()

        await ctx.author.send(embed=msg)

    @commands.command()
    async def mykeys(
        self,
        ctx: commands.Context,
    ) -> None:
        """Browse your own keys"""
        if ctx.guild:
            await ctx.author.send(
                embed=util.embed(f"This command needs to be sent in a direct message")
            )
            return

        menu: ViewMenu = util.new_view_menu(ctx)
        with self.db_sessionmaker() as session:
            member = Member.get(session, ctx.author.id, ctx.author.name)

            games: List[List[GameKeyCount]] = search.get_paginated_games(
                session=session,
                per_page=self.page_size,
                member_id=member.id,
                sort=SortOrder.TITLE,
            )

            total: int = search.count_games(session=session, member_id=member.id)

            messages: List[Embed] = util.get_page_messages(games, "Your Keys", get_page_header_text(total))

        menu.add_pages(messages)

        await menu.start()

    @commands.command()
    async def expiration(
        self,
        ctx: commands.Context,
        key: str = commands.Parameter(
            name="key",
            displayed_name="Key",
            description="The key to add an expiration date to",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        *,
        expiration: str = commands.Parameter(
            name="expiration",
            displayed_name="Expiration Date",
            description="The expiration date in MMM DD YYYY format (e.g. Dec 10 2029).",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
     ) -> None:
        """Add an expiration date to a key"""

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

        with self.db_sessionmaker() as session:
            key = search.find_key(session=session, key=key)

            if not key:
                await send_message(
                    ctx=ctx,
                    msg=util.embed(f"Key does not exist.", Colours.GOLD),
                )
                return

            if not key.creator_id == ctx.author.id:
                await send_message(
                    ctx=ctx,
                    msg=util.embed(f"Can't add expiration to someone else's key.", Colours.GOLD),
                )
                return

            try:
                expiration_date = datetime.datetime.strptime(expiration, "%b %d %Y")
            except ValueError:
                await send_message(
                    ctx=ctx,
                    msg=util.embed(f"Failed to parse expiration date.", Colours.RED),
                )
                return

            if expiration_date.date() <= datetime.datetime.now(datetime.UTC).date():
                await send_message(
                    ctx=ctx,
                    msg=util.embed(f"Expiration date is in the past.", Colours.RED),
                )
                return

            key.expiration = expiration_date
            session.commit()

        await send_message(ctx=ctx, msg=util.embed("Expiration added"))
