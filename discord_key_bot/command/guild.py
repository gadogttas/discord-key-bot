from datetime import datetime, timedelta

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Bot
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Dict, Tuple

from discord_key_bot.common import util
from discord_key_bot.db import search
from discord_key_bot.db.models import Member, Key, Game
from discord_key_bot.platform import all_platforms, pretty_platform
from discord_key_bot.common.util import get_search_arguments, GamePlatformCount
from discord_key_bot.common.colours import Colours


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
    async def search(self, ctx: commands.Context, *game_name: str):
        """Searches available games"""

        msg = util.embed("Top 15 search results...", title="Search Results")

        session: Session = self.db_session_maker()

        search_args = get_search_arguments("_".join(game_name))

        if not search_args:
            await util.send_error_message(ctx, "No game name provided!")
            return

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session, search_args=search_args, guild_id=ctx.guild.id, per_page=15
        )
        util.add_games_to_message(msg, games)

        await ctx.send(embed=msg)

    @commands.command()
    async def platforms(self, ctx: commands.Context):
        """Shows valid platforms"""

        msg: Embed = util.embed(
            f"Showing valid platforms and example key formats", title="Platforms"
        )

        for platform in all_platforms.values():
            formats = "\n".join(platform.example_keys)
            value = f"Example format(s):\n{formats}"
            msg.add_field(name=platform.name, value=value, inline=False)

        await ctx.send(embed=msg)

    @commands.command()
    async def platform(self, ctx: commands.Context, platform: str, page: int = 1):
        """Searches available games by platform"""

        if not ctx.guild:
            await ctx.send(
                embed=util.embed(
                    f"This command should be sent in a guild. To see your keys use `{self.bot.command_prefix}mykeys`"
                )
            )
            return

        platform_lower = platform.lower()

        if platform_lower not in all_platforms.keys():
            await ctx.send(
                embed=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search failed",
                )
            )
            return

        session: Session = self.db_session_maker()

        per_page = 20
        offset = (page - 1) * per_page

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session, platform=platform_lower, guild_id=ctx.guild.id, per_page=per_page, page=page,
        )

        total: int = search.count_games(
            session=session, guild_id=ctx.guild.id, platform=platform_lower
        )

        first, last = util.get_page_bounds(page, per_page, total)

        msg = util.embed(
            f"Showing {first} to {last} of {total}",
            title=f"Browse Games available for {pretty_platform(platform)}",
        )

        for game in games:
            value = f"Keys available: {game.platforms[0].count}"
            msg.add_field(name=game.name, value=value, inline=True)

        await ctx.send(embed=msg)

    @commands.command()
    async def browse(self, ctx: commands.Context, page: int = 1):
        """Browse through available games"""

        if not ctx.guild:
            await ctx.send(
                embed=util.embed(
                    f"This command should be sent in a guild. To see your keys use `{self.bot.command_prefix}mykeys`"
                )
            )
            return

        session: Session = self.db_session_maker()

        per_page: int = 20

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session, guild_id=ctx.guild.id, page=page, per_page=per_page
        )

        total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        first, last = util.get_page_bounds(page, per_page, total)

        msg: Embed = util.embed(
            f"Showing {first} to {last} of {total}", title="Browse Games"
        )
        util.add_games_to_message(msg, games)

        await ctx.send(embed=msg)

    @commands.command()
    async def random(self, ctx: commands.Context):
        """Display 20 random available games"""

        if not ctx.guild:
            await ctx.send(
                embed=util.embed(
                    f"This command should be sent in a guild. To see your keys use `{self.bot.command_prefix}mykeys`"
                )
            )
            return

        session: Session = self.db_session_maker()

        per_page: int = 20

        games: List[GamePlatformCount] = search.get_paginated_games(
            session=session, guild_id=ctx.guild.id, per_page=per_page, random=True
        )

        total: int = search.count_games(session=session, guild_id=ctx.guild.id)

        msg = util.embed(
            f"Showing {min(20, total)} random games of {total} total",
            title="Random Games",
        )

        for game in games:
            msg.add_field(name=game.name, value=game.platforms_string())

        await ctx.send(embed=msg)

    @commands.command()
    async def share(self, ctx: commands.Context):
        """Share your keys with this guild"""
        session: Session = self.db_session_maker()

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        if ctx.guild:
            if ctx.guild.id in member.guilds:
                await ctx.send(
                    embed=util.embed(
                        f"You are already sharing with {ctx.guild.name}",
                        colour=Colours.GOLD,
                    )
                )
            else:
                member.guilds.append(ctx.guild.id)
                game_count: int = search.count_games(
                    session=session, guild_id=ctx.guild.id
                )
                session.commit()
                await ctx.send(
                    embed=util.embed(
                        f"Thanks {ctx.author.name}! Your keys are now available on {ctx.guild.name}. There are now {game_count} games available.",
                        colour=Colours.GREEN,
                    )
                )
        else:
            await ctx.send(
                embed=util.embed(
                    f"You need to run this command in a guild. Not in a direct message",
                    colour=Colours.GOLD,
                )
            )

    @commands.command()
    async def unshare(self, ctx: commands.Context):
        """Remove this guild from the guilds you share keys with"""
        session: Session = self.db_session_maker()
        member: Member = Member.get(session, ctx.author.id, ctx.author.name)

        if ctx.guild:
            if ctx.guild.id not in member.guilds:
                await ctx.send(
                    embed=util.embed(
                        f"You aren't currently sharing with {ctx.guild.name}",
                        colour=Colours.GOLD,
                    )
                )
            else:
                member.guilds.remove(ctx.guild.id)
                game_count: int = search.count_games(
                    session=session, guild_id=ctx.guild.id
                )
                session.commit()
                await ctx.send(
                    embed=util.embed(
                        f"Thanks {ctx.author.name}! You have removed {ctx.guild.name} from sharing. There are now {game_count} games available.",
                        colour=Colours.GREEN,
                    )
                )
        else:
            await ctx.send(
                embed=util.embed(
                    f"You need to run this command in a guild. Not in a direct message",
                    colour=Colours.RED,
                )
            )

    @commands.command()
    async def claim(self, ctx: commands.Context, platform: str, *game_name: str):
        """Claims a game from available keys"""
        session: Session = self.db_session_maker()

        member: Member = Member.get(session, ctx.author.id, ctx.author.name)
        ready, timeleft = self._is_cooldown_elapsed(member.last_claim)
        if not ready:
            await ctx.send(
                embed=util.embed(
                    f"You must wait {timeleft} until your next claim",
                    colour=Colours.RED,
                    title="Failed to claim",
                )
            )
            return

        platform_lower: str = platform.lower()

        if platform_lower not in all_platforms.keys():
            await ctx.send(
                embed=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Failed to claim",
                )
            )
            return

        search_args: str = get_search_arguments("_".join(game_name))

        if not search_args:
            await util.send_error_message(ctx, "No game name provided!")
            return

        game_keys: Dict[str, List[Key]] = search.get_game_keys(
            session, search_args, ctx.guild.id
        )

        if not game_keys:
            await ctx.send(embed=util.embed("Game not found"))
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
        await ctx.send(
            embed=util.embed(
                f'"{game.pretty_name}" claimed by {ctx.author.name}. Check your PMs for more info. Enjoy!'
            )
        )

    def _is_cooldown_elapsed(self, timestamp: datetime) -> Tuple[bool, int]:
        if timestamp:
            cooldown_elapsed: bool = datetime.utcnow() - timestamp > self.wait_time
            time_remaining: int = timestamp + self.wait_time - datetime.utcnow()

            return cooldown_elapsed, time_remaining

        return True, 0
