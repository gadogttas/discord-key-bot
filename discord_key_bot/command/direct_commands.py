from itertools import groupby

from discord.ext import commands

from discord_key_bot.common import util
from discord_key_bot.db import Session
from discord_key_bot.db.models import Game, Key, Member
from discord_key_bot.keyparse import parse_key, keyspace, parse_name
from discord_key_bot.common.colours import Colours

class DirectCommands(commands.Cog):
    """Run these commands in private messages to the bot"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def add(self, ctx, key, *game_name):
        """Add a key"""
        session = Session()

        pretty_name = " ".join(game_name)

        if not await util.validate_search_args(pretty_name, ctx):
            return

        game = Game.get(session, pretty_name)

        platform, key = parse_key(key)

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

        if not platform:
            await ctx.send(embed=util.embed(key, Colours.RED))
            return

        found = session.query(Key).filter(Key.key == key).count()

        if found:
            await ctx.send(
                embed=util.embed(
                    f"Key already exists!",
                    Colours.GOLD,
                )
            )
            return

        member = Member.get(session, ctx.author.id, ctx.author.name)

        game.keys.append(Key(platform=platform, key=key, creator=member, game=game))

        session.commit()

        await ctx.author.send(
            embed=util.embed(
                f'Key for "{game.pretty_name}" added. Thanks {ctx.author.name}!',
                Colours.GREEN,
                title=f"{platform.title()} Key Added",
            )
        )

    @commands.command()
    async def remove(self, ctx, platform, *game_name):
        """Remove a key and send to you in a PM"""

        platform_lower = platform.lower()

        if platform_lower not in keyspace.keys():
            await ctx.send(
                embed=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search Error",
                )
            )
            return

        search_args = parse_name("_".join(game_name))

        if not await util.validate_search_args(search_args, ctx):
            return

        session = Session()

        member = Member.get(session, ctx.author.id, ctx.author.name)

        game = (
            session.query(Game)
            .join(Key)
            .filter(
                Game.name == search_args,
                Key.platform == platform_lower,
                Key.creator_id == member.id,
            )
            .first()
        )

        if game:
            game = {
                k: list(v) for k, v in groupby(game.keys, lambda x: x.platform)
            }

        if not game:
            await ctx.send(embed=util.embed("Game not found"))
            return

        key = game[platform_lower][0]
        game = key.game

        msg = util.embed(
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
    async def mykeys(self, ctx, page=1):
        """Browse your own keys"""
        if ctx.guild:
            await ctx.author.send(
                embed=util.embed(f"This command needs to be sent in a direct message")
            )
            return

        session = Session()
        member = Member.get(session, ctx.author.id, ctx.author.name)

        per_page = 15
        offset = (page - 1) * per_page

        query = (
            session.query(Key)
            .join(Game)
            .filter(Key.creator_id == member.id)
            .order_by(Game.pretty_name.asc(), Key.platform.asc())
        )

        first = offset + 1
        total = query.count()
        last = min(page * per_page, total)

        msg = util.embed(f"Showing {first} to {last} of {total}")

        for k in query.limit(per_page).offset(offset).all():
            msg.add_field(name=f"{k.game.pretty_name}", value=f"{k.platform.title()}")

        await ctx.send(embed=msg)