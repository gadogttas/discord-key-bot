import inspect
import datetime

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from sqlalchemy.orm import sessionmaker
from typing import List, Optional

from discord_key_bot.common import util
from discord_key_bot.db import search
from discord_key_bot.db.models import Member, Key, Game
from discord_key_bot.db.queries import SortOrder
from discord_key_bot.platform import all_platforms, get_platform, Platform
from discord_key_bot.common.util import GamePlatformCount, send_message, get_page_header_text
from discord_key_bot.common.colours import Colours


class GuildCommands(commands.Cog, name='Channel Commands'):
    def __init__(
        self,
        bot: Bot,
        db_sessionmaker: sessionmaker,
        wait_time: datetime.timedelta,
        page_size: int,
    ):
        self.bot: Bot = bot
        self.wait_time: datetime.timedelta = wait_time
        self.db_sessionmaker: sessionmaker = db_sessionmaker
        self.page_size: int = page_size

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

        with self.db_sessionmaker() as session:
            games: List[GamePlatformCount] = search.get_paginated_games(
                session=session,
                title=game_name,
                guild_id=ctx.guild.id,
                per_page=self.page_size,
                sort=SortOrder.TITLE,
            )

        msg = util.build_page_message(
            title="Search Results",
            text=f"Top {self.page_size} search results...",
            games=games
        )

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def platforms(self, ctx: commands.Context) -> None:
        """Shows valid platforms"""

        msg: Embed = util.embed(
            f"Showing valid platforms and example key formats", title="Platforms"
        )

        for platform in all_platforms():
            formats = "\n".join(platform.example_keys)
            value = f"Example format(s):\n{formats}"
            msg.add_field(name=platform.name, value=value, inline=False)

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def platform(
        self,
        ctx: commands.Context,
        platform_name: str = commands.Parameter(
            name="platform_name",
            displayed_name="Platform",
            description="The platform you wish to see games for (e.g. Steam)",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        page: int = commands.Parameter(
            name="page",
            displayed_name="Page Number",
            description=f"The page number to display",
            kind=inspect.Parameter.POSITIONAL_ONLY,
            default=1,
        ),
    ) -> None:
        """Lists available games for the specified platform"""

        try:
            platform: Platform = get_platform(platform_name)
        except ValueError:
            await send_message(
                ctx=ctx,
                msg=util.embed(
                    f'"{platform_name}" is not valid platform',
                    colour=Colours.RED,
                    title="Search failed",
                ),
            )
            return

        with self.db_sessionmaker() as session:
            games: List[GamePlatformCount] = search.get_paginated_games(
                session=session,
                platform=platform,
                guild_id=ctx.guild.id,
                per_page=self.page_size,
                page=page,
                sort=SortOrder.TITLE,
            )

            total: int = search.count_games(
                session=session, guild_id=ctx.guild.id, platform=platform
            )

        msg = util.embed(
            get_page_header_text(page, total, self.page_size),
            title=f"Browse Games available for {platform.name}",
        )

        for game in games:
            value = f"Keys available: {game.platforms[0].count}"
            msg.add_field(name=game.name, value=value, inline=True)

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def browse(
        self,
        ctx: commands.Context,
        page: int = commands.Parameter(
            name="page",
            displayed_name="Page Number",
            description="The page number",
            kind=inspect.Parameter.POSITIONAL_ONLY,
            default=1,
        ),
    ) -> None:
        """Browse through available games"""

        with self.db_sessionmaker() as session:
            games: List[GamePlatformCount] = search.get_paginated_games(
                session=session,
                guild_id=ctx.guild.id,
                page=page,
                per_page=self.page_size,
                sort=SortOrder.TITLE,
            )

            total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg: Embed = util.build_page_message(
            title="Browse Games",
            text=get_page_header_text(page, total, self.page_size),
            games=games,
        )

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def latest(
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
        """Browse through available games by date added in descending order"""

        with self.db_sessionmaker() as session:
            games: List[GamePlatformCount] = search.get_paginated_games(
                session=session,
                guild_id=ctx.guild.id,
                page=page,
                per_page=self.page_size,
                sort=SortOrder.LATEST,
            )

            total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg: Embed = util.build_page_message(
            title="Latest Games",
            text=get_page_header_text(page, total, self.page_size),
            games=games,
        )

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def random(self, ctx: commands.Context) -> None:
        """Display random available games"""

        with self.db_sessionmaker() as session:
            games: List[GamePlatformCount] = search.get_paginated_games(
                session=session,
                guild_id=ctx.guild.id,
                per_page=self.page_size,
                sort=SortOrder.RANDOM,
            )

            total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg = util.embed(
            f"Showing {min(self.page_size, total)} random games of {total} total",
            title="Random Games",
        )

        for game in games:
            msg.add_field(name=game.name, value=game.platforms_string())

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def share(self, ctx: commands.Context) -> None:
        """Share your keys with this guild"""

        with self.db_sessionmaker() as session:
            member: Member = Member.get(session, ctx.author.id, ctx.author.name)
            if ctx.guild.id in member.guilds:
                await send_message(
                    ctx=ctx,
                    msg=util.embed(f"You are already sharing with {ctx.guild.name}", colour=Colours.GOLD)
                )
            else:
                member.guilds.append(ctx.guild.id)
                game_count: int = search.count_games(
                    session=session, guild_id=ctx.guild.id
                )
                session.commit()
                await send_message(
                    ctx=ctx,
                    msg=util.embed(
                        f"Thanks {ctx.author.name}! Your keys are now available on {ctx.guild.name}. There are now {game_count} games available.",
                        colour=Colours.GREEN,
                    )
                )

    @commands.command()
    async def unshare(self, ctx: commands.Context) -> None:
        """Remove this guild from the guilds you share keys with"""
        with self.db_sessionmaker() as session:
            member: Member = Member.get(session, ctx.author.id, ctx.author.name)

            if ctx.guild.id not in member.guilds:
                await send_message(
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
                await send_message(
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
        platform_name: str = commands.Parameter(
            name="platform_name",
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
        with self.db_sessionmaker() as session:
            member: Member = Member.get(session, ctx.author.id, ctx.author.name)

            timeleft = self._get_cooldown(member)
            if timeleft.total_seconds() > 0:
                await send_message(
                    ctx=ctx,
                    msg=util.embed(
                        f"You must wait {util.pretty_timedelta(timeleft)} until your next claim",
                        colour=Colours.RED,
                        title="Failed to claim",
                    ),
                )
                return

            try:
                platform: Platform = get_platform(platform_name)
            except ValueError:
                await send_message(
                    ctx=ctx,
                    msg=util.embed(
                        f'"{platform_name}" is not valid platform',
                        colour=Colours.RED,
                        title="Failed to claim",
                    ),
                )
                return

            game: Optional[Game] = search.get_game(
                session, game_name, ctx.guild.id
            )

            if not game:
                await send_message(ctx=ctx, msg=util.embed("Game not found"))
                return

            try:
                key: Key = game.find_key_by_platform(platform)
            except ValueError:
                await send_message(ctx=ctx, msg=util.embed("No keys found for the specified platform"))
                return

            msg: Embed = util.embed(
                f"Please find your key below", title="Game claimed!", colour=Colours.GREEN
            )

            msg.add_field(name=game.pretty_name, value=key.key)

            session.delete(key)
            session.refresh(game)

            if not game.keys:
                session.delete(game)

            if key.creator_id != member.id:
                member.last_claim = datetime.datetime.now(datetime.UTC)
            session.commit()

        await ctx.author.send(embed=msg)
        await send_message(
            ctx=ctx,
            msg=util.embed(
                f'"{game.pretty_name}" claimed by {ctx.author.display_name}. Check your PMs for more info. Enjoy!'
            ),
        )

    @commands.command()
    async def imfeelinglucky(
            self,
            ctx: commands.Context,
            platform_name: str = commands.Parameter(
                name="platform_name",
                displayed_name="Platform",
                description="The platform you wish to find a game for (e.g. Steam)",
                kind=inspect.Parameter.POSITIONAL_ONLY,
            ),
    ) -> None:
        """Display a single random game for the requested platform"""

        try:
            platform: Platform = get_platform(platform_name)
        except ValueError:
            await send_message(
                ctx=ctx,
                msg=util.embed(
                    text=f'"{platform_name}" is not valid platform',
                    colour=Colours.RED,
                    title="Not that lucky, I guess.",
                ),
            )
            return

        with self.db_sessionmaker() as session:
            games: List[GamePlatformCount] = search.get_paginated_games(
                session=session,
                guild_id=ctx.guild.id,
                platform=platform,
                per_page=1,
                sort=SortOrder.RANDOM,
            )

            total: int = search.count_games(session=session, guild_id=ctx.guild.id, platform=platform)

        msg = util.embed(
            f"Showing one random game of {total} total",
            title="Well, are you?",
        )

        if not games:
            await send_message(ctx=ctx, msg=util.embed("No games found"))
            return

        msg.add_field(name=games[0].name, value=games[0].platforms_string())

        await send_message(ctx=ctx, msg=msg)

    @commands.command()
    async def expiring(
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
        """Keys expiring soon"""

        keys: List[Key]
        count: int

        with self.db_sessionmaker() as session:
            keys, count = search.get_expiring_keys(
                session=session,
                guild_id=ctx.guild.id,
                page=page,
                per_page=self.page_size,
            )

            if not keys:
                await send_message(ctx=ctx, msg=util.embed("No keys found"))
                return

            msg: Embed = util.embed(title="Expiring Keys",
                                    text=get_page_header_text(page, count, self.page_size, "keys"))

            for key in keys:
                platform: Platform = get_platform(key.platform)
                datestr: str = datetime.datetime.strftime(key.expiration, "%b %d %Y")
                msg.add_field(
                    name=key.game.pretty_name,
                    value=f"{platform.name} : {datestr}"
                )

        await send_message(ctx=ctx, msg=msg)

    def _get_cooldown(self, member: Member) -> datetime.timedelta:
        if member.last_claim:
            last_claim: datetime = member.last_claim.replace(tzinfo=datetime.UTC)
            return last_claim - datetime.datetime.now(datetime.UTC) + self.wait_time

        return datetime.timedelta(0)
