import inspect
from datetime import datetime, timedelta

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from loguru import logger
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Dict, Tuple

from discord_key_bot.common import util
from discord_key_bot.common.constants import DEFAULT_PAGE_SIZE
from discord_key_bot.db import search
from discord_key_bot.db.models import Member, Key, Game
from discord_key_bot.db.queries import SortOrder
from discord_key_bot.platform import all_platforms, pretty_platform
from discord_key_bot.common.util import GamePlatformCount, send_with_retry, get_page_header_text
from discord_key_bot.common.colours import Colours


log: logger = logger.bind(name='guild')

class GuildCommands(commands.Cog):
    def __init__(
        self,
        bot: Bot,
        db_session_maker: sessionmaker,
        bot_channel_id: int,
        wait_time: timedelta,
    ):
        self.bot: Bot = bot
        self.bot_channel_id: int = bot_channel_id
        self.wait_time: timedelta = wait_time
        self.db_session_maker: sessionmaker = db_session_maker

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        if self.bot_channel_id and ctx.channel.id != self.bot_channel_id:
            raise commands.CommandError("wrong channel")

    @commands.command()
    async def search(
        self,
        ctx: commands.Context,
        *,
        game_name: str = commands.Parameter(
            name="game_name",
            displayed_name="Game Name",
            description="The name of the game you wish to search for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
    ) -> None:
        """Search available games"""

        log.debug(f"Received 'search' request: author_id={ctx.author.id}, game_name={game_name}")

        session: Session = self.db_session_maker()

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            title=game_name,
            guild_id=ctx.guild.id,
            per_page=DEFAULT_PAGE_SIZE,
            sort=SortOrder.TITLE,
        )

        msg = util.build_page_message(
            title="Search Results",
            text=f"Top {DEFAULT_PAGE_SIZE} search results...",
            games=games
        )

        await send_with_retry(ctx=ctx, msg=msg)

    @commands.command()
    async def platforms(self, ctx: commands.Context) -> None:
        """Shows valid platforms"""

        log.debug(f"Received 'platforms' request: author_id={ctx.author.id}")

        msg: Embed = util.embed(
            f"Showing valid platforms and example key formats", title="Platforms"
        )

        for platform in all_platforms.values():
            formats = "\n".join(platform.example_keys)
            value = f"Example format(s):\n{formats}"
            msg.add_field(name=platform.name, value=value, inline=False)

        await send_with_retry(ctx=ctx, msg=msg)

    @commands.command()
    async def platform(
        self,
        ctx: commands.Context,
        platform: str = commands.Parameter(
            name="platform",
            displayed_name="Platform",
            description="The platform you wish to see games for (e.g. Steam)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        page: int = commands.Parameter(
            name="page",
            displayed_name="Page Number",
            description=f"The page number to display ({DEFAULT_PAGE_SIZE} games per page)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
            default=1,
        ),
    ) -> None:
        """Lists available games for the specified platform"""

        log.debug(f"Received 'platform' request: author_id={ctx.author.id}, platform={platform}, page={page}")

        platform_lower = platform.lower()

        if platform_lower not in all_platforms.keys():
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search failed",
                ),
            )
            return

        session: Session = self.db_session_maker()

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            platform=platform_lower,
            guild_id=ctx.guild.id,
            per_page=DEFAULT_PAGE_SIZE,
            page=page,
            sort=SortOrder.TITLE,
        )

        total: int = search.count_games(
            session=session, guild_id=ctx.guild.id, platform=platform_lower
        )

        msg = util.embed(
            get_page_header_text(page, total, DEFAULT_PAGE_SIZE),
            title=f"Browse Games available for {pretty_platform(platform)}",
        )

        for game in games:
            value = f"Keys available: {game.platforms[0].count}"
            msg.add_field(name=game.name, value=value, inline=True)

        await send_with_retry(ctx=ctx, msg=msg)

    @commands.command()
    async def browse(
        self,
        ctx: commands.Context,
        page: int = commands.Parameter(
            name="page",
            displayed_name="Page Number",
            description="The page number ({DEFAULT_PAGE_SIZE} per page)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
            default=1,
        ),
    ) -> None:
        """Browse through available games"""

        log.debug(f"Received 'browse' request: author_id={ctx.author.id}, page={page}")

        session: Session = self.db_session_maker()

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            guild_id=ctx.guild.id,
            page=page,
            per_page=DEFAULT_PAGE_SIZE,
            sort=SortOrder.TITLE,
        )

        total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg: Embed = util.build_page_message(
            title="Browse Games",
            text=get_page_header_text(page, total, DEFAULT_PAGE_SIZE),
            games=games,
        )

        await send_with_retry(ctx=ctx, msg=msg)

    @commands.command()
    async def latest(
        self,
        ctx: commands.Context,
        page: int = commands.Parameter(
            name="page",
            displayed_name="Page Number",
            description=f"The page number ({DEFAULT_PAGE_SIZE} games per page)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
            default=1,
        ),
    ) -> None:
        """Browse through available games by date added in descending order"""

        log.debug(f"Received 'latest' request: author_id={ctx.author.id}, page={page}")

        session: Session = self.db_session_maker()

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            guild_id=ctx.guild.id,
            page=page,
            per_page=DEFAULT_PAGE_SIZE,
            sort=SortOrder.LATEST,
        )

        total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg: Embed = util.build_page_message(
            title="Latest Games",
            text=get_page_header_text(page, total, DEFAULT_PAGE_SIZE),
            games=games,
        )

        await send_with_retry(ctx=ctx, msg=msg)

    @commands.command()
    async def random(self, ctx: commands.Context) -> None:
        """Display 20 random available games"""

        log.debug(f"Received 'random' request: author_id={ctx.author.id}")

        session: Session = self.db_session_maker()

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session,
            guild_id=ctx.guild.id,
            per_page=DEFAULT_PAGE_SIZE,
            sort=SortOrder.RANDOM,
        )

        total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg = util.embed(
            f"Showing {min(20, total)} random games of {total} total",
            title="Random Games",
        )

        for game in games:
            msg.add_field(name=game.name, value=game.platforms_string())

        await send_with_retry(ctx=ctx, msg=msg)

    @commands.command()
    async def share(self, ctx: commands.Context) -> None:
        """Share your keys with this guild"""
        session: Session = self.db_session_maker()

        log.debug(f"Received 'share' request: author_id={ctx.author.id}")

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        if ctx.guild.id in member.guilds:
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(f"You are already sharing with {ctx.guild.name}", colour=Colours.GOLD)
            )
        else:
            member.guilds.append(ctx.guild.id)
            game_count: int = search.count_games(
                session=session, guild_id=ctx.guild.id
            )
            session.commit()
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f"Thanks {ctx.author.name}! Your keys are now available on {ctx.guild.name}. There are now {game_count} games available.",
                    colour=Colours.GREEN,
                )
            )

    @commands.command()
    async def unshare(self, ctx: commands.Context) -> None:
        """Remove this guild from the guilds you share keys with"""

        log.debug(f"Received 'unshare' request: author_id={ctx.author.id}")

        session: Session = self.db_session_maker()
        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        if ctx.guild.id not in member.guilds:
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f"You aren't currently sharing with {ctx.guild.name}",
                    colour=Colours.GOLD,
                ),
            )
        else:
            member.guilds.remove(ctx.guild.id)
            game_count: int = search.count_games(session=session, guild_id=ctx.guild.id)
            session.commit()
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f"Thanks {ctx.author.name}! You have removed {ctx.guild.name} from sharing. There are now {game_count} games available.",
                    colour=Colours.GREEN,
                ),
            )

    @commands.command()
    async def claim(
        self,
        ctx: commands.Context,
        platform: str = commands.Parameter(
            name="platform",
            displayed_name="Platform",
            description="The platform you wish to claim a key for (e.g. Steam)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        *,
        game_name: str = commands.Parameter(
            name="game_name",
            displayed_name="Game Name",
            description="The name of the game you wish to claim a key for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
    ) -> None:
        """Claims a game from available keys"""

        log.debug(f"Received 'claim' request: author_id={ctx.author.id}, game_name={game_name}")

        session: Session = self.db_session_maker()

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)
        ready, timeleft = self._is_cooldown_elapsed(member.last_claim)
        if not ready:
            log.debug(f"User cooldown has not elapsed: author_id={ctx.author.id}")

            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f"You must wait {timeleft} until your next claim",
                    colour=Colours.RED,
                    title="Failed to claim",
                ),
            )
            return

        platform_lower: str = platform.lower()

        if platform_lower not in all_platforms.keys():
            await send_with_retry(
                ctx=ctx,
                msg=util.embed(
                    f'"{platform}" is not valid platform', colour=Colours.RED, title="Failed to claim",
                ),
            )
            return

        game_keys: Dict[str, List[Key]] = search.get_game_keys(
            session, game_name, ctx.guild.id
        )   

        if not game_keys:
            await send_with_retry(ctx=ctx, msg=util.embed("Game not found"))
            return

        key: Key = game_keys[platform_lower][0]
        game: Game = key.game

        msg: Embed = util.embed(
            f"Please find your key below", title="Game claimed!", colour=Colours.GREEN
        )

        msg.add_field(name=game.pretty_name, value=key.key)

        session.delete(key)
        session.commit()

        if not game.keys:
            session.delete(game)

        if key.creator_id != member.id:
            member.last_claim = datetime.utcnow()
        session.commit()

        await ctx.author.send(embed=msg)
        await send_with_retry(
            ctx=ctx,
            msg=util.embed(
                f'"{game.pretty_name}" claimed by {ctx.author.name}. Check your PMs for more info. Enjoy!'
            ),
        )

        log.debug(f"Key claim successful: author_id={ctx.author.id}, game_name={game_name}")

    def _is_cooldown_elapsed(self, timestamp: datetime) -> Tuple[bool, timedelta]:
        if timestamp:
            cooldown_elapsed: bool = datetime.utcnow() - timestamp > self.wait_time
            time_remaining: timedelta = timestamp + self.wait_time - datetime.utcnow()

            return cooldown_elapsed, time_remaining

        return True, timedelta()
