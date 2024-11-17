import datetime
import inspect
import logging
import re
from typing import Sequence, Optional

import discord
from discord import User
from discord.ext import commands
from discord.ext.commands import Bot
from sqlalchemy.orm import sessionmaker, Session

from discord_key_bot.command.util import is_admin
from discord_key_bot.common.colours import Colours
from discord_key_bot.common.util import get_search_name, embed, send_message
from discord_key_bot.db import search
from discord_key_bot.db.models import Game, Member
from discord_key_bot.platform import Platform, get_platform


class AdminCommands(commands.Cog, name='Admin Commands', command_attrs=dict(hidden=True)):
    def __init__(self, bot: Bot, db_session_maker: sessionmaker, admin_role_id: int = 0):
        self.bot: Bot = bot
        self.db_sessionmaker: sessionmaker = db_session_maker
        self.logger = logging.getLogger(__name__)
        self.admin_role_id = admin_role_id

        self._member_patt = re.compile(r"<@(\d+)>")

    @commands.is_owner()
    @commands.command()
    async def addadmin(
        self,
        ctx: commands.Context,
        *,
        member: str = commands.Parameter(
            name="member",
            displayed_name="Member",
            description="Member to add as admin",
            kind=inspect.Parameter.POSITIONAL_ONLY
        ),
    ):
        """Add a member as an admin"""

        self.logger.info(f"received addadmin request from user {ctx.author.display_name}")

        user: User = await self._get_user(ctx, member)
        if not user:
            return

        session: Session = self.db_sessionmaker()

        member = Member.get(session, user.id, user.name)
        member.is_admin = True

        session.flush()
        session.commit()

        await ctx.author.send(embed=embed(f"Successfully added {user.name} as admin", colour=Colours.GREEN))

    @commands.is_owner()
    @commands.command()
    async def rmadmin(
        self,
        ctx: commands.Context,
        *,
        member: str = commands.Parameter(
            name="member",
            displayed_name="Member",
            description="Member to remove as admin",
            kind=inspect.Parameter.POSITIONAL_ONLY
        ),
    ):
        """Remove a member as an admin"""

        self.logger.info(f"received rmadmin request from user {ctx.author.display_name}")

        user: User = await self._get_user(ctx, member)
        if not user:
            return

        session: Session = self.db_sessionmaker()

        member = Member.get(session, user.id, user.name)
        member.is_admin = False

        session.flush()
        session.commit()

        await ctx.author.send(embed=embed(f"Successfully removed {user.name} as admin", colour=Colours.GREEN))

    @commands.command()
    @commands.is_owner()
    async def lsadmin(self, ctx: commands.Context):
        """List admin users"""

        self.logger.info(f"received lsadmin request from user {ctx.author.display_name}")

        session: Session = self.db_sessionmaker()

        admin_users: Sequence[Member] = search.get_admin_members(session)

        if not admin_users:
            await ctx.author.send(embed=embed("No admin users found", colour=Colours.RED))
            return

        msg = embed(
            title="Admin Users",
            text="",
            colour=Colours.GREEN
        )

        for admin in admin_users:
            msg.add_field(name=admin.name,
                          value=f"**id:** {admin.id}")

        await ctx.author.send(embed=msg)

    @commands.command()
    async def gameid(
        self,
        ctx: commands.Context,
        *,
        game_name: str = commands.Parameter(
            name="game_name",
            displayed_name="Game Name",
            description="The name of the game you wish to get IDs for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
     ):
        """Load game IDs"""

        self.logger.info(f"received gameinfo request from user {ctx.author.display_name}")

        session: Session = self.db_sessionmaker()

        if not is_admin(session, ctx):
            self.logger.info(f"{ctx.author.display_name} is not an authorized admin")
            return

        games: Sequence[Game] = search.get_admin_games(
            session=session, game_name=game_name
        )

        if not games:
            await ctx.author.send(embed=embed("Game not found", colour=Colours.RED))
            return

        msg = embed(
            title="Game Info",
            text="",
            colour=Colours.GREEN
        )

        for game in games:
            msg.add_field(name=game.pretty_name,
                          value=f"**id:** {game.id}")

        await ctx.author.send(embed=msg)

    @commands.command()
    @commands.is_owner()
    async def rename(
        self,
        ctx: commands.Context,
        game_id: int = commands.Parameter(
            name="game_id",
            displayed_name="Game ID",
            description="The ID of the game to rename",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        *,
        new_name: str = commands.Parameter(
            name="new_name",
            displayed_name="New Name",
            description="New name for for the renamed game",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
    ):
        """Rename a game"""

        self.logger.info(
            f"received rename request from user {ctx.author.display_name} to rename game_id {game_id} to {new_name}")

        session: Session = self.db_sessionmaker()

        if not is_admin(session, ctx):
            self.logger.info(f"{ctx.author.display_name} is not an authorized admin")
            return


        game = session.get(Game, game_id)

        if not game:
            await ctx.author.send(embed=embed("Game not found", colour=Colours.RED))
            return

        if game.name == get_search_name(new_name):
            game.pretty_name = new_name
            session.flush()
            session.commit()

            text: str = f"Renamed display name of existing game from '{game.pretty_name}' to '{new_name}'"
            self.logger.debug(text)
            await ctx.author.send(embed=embed(title="Renamed game", text=text))
            return

        existing_game = search.get_game(session=session, game_name=new_name)
        if not existing_game:
            text: str = f"Renaming names of existing game from '{game.pretty_name}' to '{new_name}'"
            game.pretty_name = new_name
            game.name = get_search_name(new_name)

            self.logger.debug(text)
            await ctx.author.send(embed=embed(title="Renamed game", text=text))
        else:
            text: str = f"Moving keys from game ID {game.id} to game ID {existing_game.id}"
            self.logger.debug(text)
            await ctx.author.send(embed=embed(title="Renaming game", text=text))

            for key in game.keys:
                key.game_id = existing_game.id
                key.game = existing_game

            session.delete(game)

        session.flush()
        session.commit()

    @commands.command()
    async def bulk_expire(
        self,
        ctx: commands.Context,
        game_id: int = commands.Parameter(
            name="game_id",
            displayed_name="Game ID",
            description="The ID of the game to set expiration for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        platform_name: str = commands.Parameter(
            name="platform_name",
            displayed_name="Platform Name",
            description=f"The platform game to set expiration for",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
        *,
        expiration: str = commands.Parameter(
            name="expiration",
            displayed_name="Expiration Date",
            description="The expiration date in MMM DD YYYY format (e.g. Dec 10 2029).",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        ),
    ):
        """Set expiration on all keys for a given platform"""

        self.logger.info(f"bulk_expire request from user {ctx.author.display_name}: {game_id} - {expiration}")

        session: Session = self.db_sessionmaker()

        if not is_admin(session, ctx):
            self.logger.info(f"{ctx.author.display_name} is not an authorized admin")
            return

        try:
            platform: Platform = get_platform(platform_name)
        except ValueError:
            await ctx.author.send(
                embed=embed(f'"{platform_name}" is not valid platform', Colours.RED),
            )
            return

        game = session.get(Game, game_id)
        if not game:
            await ctx.author.send(embed=embed("Game not found", colour=Colours.RED))
            return

        try:
            expiration_date = datetime.datetime.strptime(expiration, "%b %d %Y")
        except ValueError:
            await send_message(
                ctx=ctx,
                msg=embed(f"Failed to parse expiration date.", Colours.RED),
            )
            return

        if expiration_date.date() <= datetime.datetime.now(datetime.UTC).date():
            await send_message(
                ctx=ctx,
                msg=embed(f"Expiration date is in the past.", Colours.RED),
            )
            return

        for key in game.keys:
            if key.platform == platform.search_name:
                key.expiration = expiration_date

        session.flush()
        session.commit()

        await send_message(
            ctx=ctx,
            msg=embed(f"Set bulk expiration dates", Colours.RED),
        )

    @commands.command()
    @commands.is_owner()
    async def purge(self, ctx: commands.Context):
        """Purge expired keys and orphaned games"""

        self.logger.info(f"purge request from user {ctx.author.display_name}")

        session: Session = self.db_sessionmaker()

        game_count: int
        key_count: int
        game_count, key_count = search.delete_expired(session)
        session.flush()
        session.commit()

        await ctx.author.send(
            embed=embed(
                title="Deleting Expired Keys",
                text=f"{game_count} games, {key_count} keys deleted", colour=Colours.GREEN)
            )

    @commands.command()
    async def delete(
        self,
        ctx: commands.Context,
        game_id: int = commands.Parameter(
            name="game_id",
            displayed_name="Game ID",
            description="The ID of the game to delete",
            kind=inspect.Parameter.POSITIONAL_ONLY,
        )
    ):
        """Purge expired keys and orphaned games"""

        self.logger.info(f"delete request from user {ctx.author.display_name} for game_id {game_id}")

        session: Session = self.db_sessionmaker()

        if not is_admin(session, ctx):
            self.logger.info(f"{ctx.author.display_name} is not an authorized admin")
            return

        game = session.get(Game, game_id)
        if not game:
            await ctx.author.send(embed=embed("Game not found", colour=Colours.RED))
            return

        session.delete(game)
        session.flush()
        session.commit()

        await ctx.author.send(
            embed=embed(
                title="Deleting Expired Keys",
                text=f"game_id {game_id} deleted", colour=Colours.GREEN)
            )

    async def _get_user(self, ctx: commands.Context, user_str: str) -> Optional[discord.User]:
        match: re.Match = self._member_patt.match(user_str)
        if not match:
            await ctx.author.send(embed=embed("Invalid member", colour=Colours.RED))
            return None

        user_id: int
        try:
            user_id = int(match.group(1))
        except ValueError:
            await ctx.author.send(embed=embed("Invalid member ID", colour=Colours.RED))
            return None

        user: User = await self.bot.fetch_user(user_id)
        if not user:
            await ctx.author.send(embed=embed("No user found with the provided ID", colour=Colours.RED))
            return None

        return user
