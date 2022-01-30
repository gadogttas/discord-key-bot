import os
from collections import defaultdict
from itertools import groupby
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from .db import Session, func
from .db.models import Game, Key, Member, Guild
from .keyparse import parse_key, keyspace, parse_name, examples
from .colours import Colours

COMMAND_PREFIX = os.environ.get("BANG", "!")

bot = commands.Bot(command_prefix=COMMAND_PREFIX)

WAIT_TIME = timedelta(seconds=int(os.environ.get("WAIT_TIME", 86400)))
BOT_CHANNEL_NAME = os.environ.get("BOT_CHANNEL_NAME")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"**Invalid command. Try using** `{COMMAND_PREFIX}help` **to figure out commands.**")
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"**Please pass in all requirements. Use** `{COMMAND_PREFIX}help {ctx.invoked_with}` **to see requirements.**")


async def _validate_search_args(search_args, ctx):
    if not search_args:
        await ctx.send(embed=embed("No game name provided!", Colours.RED))
        return False
    
    if len(search_args) < 3:
        await ctx.send(
            embed=embed(
                "Game name must be at least 3 characters.",
                Colours.RED
            )
        )
        return False

    return True


def claimable(timestamp):
    if timestamp:
        return (
            datetime.utcnow() - timestamp > WAIT_TIME,
            timestamp + WAIT_TIME - datetime.utcnow(),
        )
    else:
        return True, None


def embed(text, colour=Colours.DEFAULT, title="Keybot"):
    msg = discord.Embed(title=title, type="rich", description=text, color=colour)

    return msg


def find_games(session, search_args, guild_id, limit=15, offset=None):
    query = (
        session.query(Game)
        .join(Key)
        .filter(
            Key.creator_id.in_(
                session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id)
            )
        )
        .filter(Game.name.like(f"%{search_args}%"))
        .order_by(func.lower(Game.pretty_name).asc())
    )

    if offset is None:
        games = defaultdict(lambda: defaultdict(list))

        for g in query.from_self().offset(offset).limit(limit).all():
            games[g.pretty_name] = {
                k: list(v) for k, v in groupby(g.keys, lambda x: x.platform)
            }
    else:
        games = None

    return games, query
    

def get_random_games(session, guild_id, limit=15):
    query = (
        session.query(Game)
        .join(Key)
        .filter(
            Key.creator_id.in_(
                session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id)
            )
        )
        .order_by(func.random())
    )

    games = defaultdict(lambda: defaultdict(list))

    for g in query.from_self().limit(limit).all():
        games[g.pretty_name] = {
            k: list(v) for k, v in groupby(g.keys, lambda x: x.platform)
        }

    return games, query


def find_games_by_platform(session, platform, guild_id, limit=15, offset=None):
    query = (
        session.query(Game.pretty_name, func.count(Game.pretty_name).label('count'))
        .join(Key)
        .filter(
            Key.creator_id.in_(
                session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id)
            )
        )
        .filter(Key.platform == platform.lower())
        .group_by(Game.pretty_name)
        .order_by(func.lower(Game.pretty_name).asc())
    )

    games = {}

    for g in query.from_self().offset(offset).limit(limit).all():
        games[g.pretty_name] = g.count

    return games, query


class GuildCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx):
        if (BOT_CHANNEL_NAME and str(ctx.channel) != BOT_CHANNEL_NAME):
            raise commands.CommandError('wrong channel')

    @commands.command()
    async def search(self, ctx, *game_name):
        """Searches available games"""

        msg = embed("Top 15 search results...", title="Search Results")

        session = Session()

        search_args = parse_name("_".join(game_name))

        if not await _validate_search_args(search_args, ctx):
            return

        games, _ = find_games(session, search_args, ctx.guild.id)

        for g, platforms in games.items():
            value = "\n".join(f"{p.title()}: {len(c)}" for p, c in platforms.items())
            msg.add_field(name=g, value=value, inline=True)

        await ctx.send(embed=msg)

    @commands.command()
    async def platforms(self, ctx):
        """Shows valid platforms"""
        
        msg = embed(f"Showing valid platforms and example key formats", title="Platforms")
        
        for p, ex in examples.items():
            formats = '\n'.join(ex)
            value = f"Example format(s):\n{formats}"
            msg.add_field(name=p, value=value, inline=False)
            
        await ctx.send(embed=msg)

    @commands.command()
    async def platform(self, ctx, platform, page=1):
        """Searches available games by platform"""

        if not ctx.guild:
            await ctx.send(
                embed=embed(
                    f"This command should be sent in a guild. To see your keys use `{COMMAND_PREFIX}mykeys`"
                )
            )
            return

        platform_lower = platform.lower()

        if platform_lower not in keyspace.keys():
            await ctx.send(
                embed=embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search failed",
                )
            )
            return

        session = Session()

        per_page = 20
        offset = (page - 1) * per_page

        games, query = find_games_by_platform(session, platform_lower, ctx.guild.id, per_page, offset)

        first = offset + 1
        total = query.count()
        last = min(page * per_page, total)

        msg = embed(f"Showing {first} to {last} of {total}", title=f"Browse Games available for {platform}")

        for g, count in games.items():
            value = f"Keys available: {count}"
            msg.add_field(name=g, value=value, inline=True)

        await ctx.send(embed=msg)

    @commands.command()
    async def browse(self, ctx, page=1):
        """Browse through available games"""

        if not ctx.guild:
            await ctx.send(
                embed=embed(
                    f"This command should be sent in a guild. To see your keys use `{COMMAND_PREFIX}mykeys`"
                )
            )
            return

        session = Session()

        per_page = 20
        offset = (page - 1) * per_page

        games, query = find_games(session, "", ctx.guild.id, per_page, offset)

        first = offset + 1
        total = query.count()
        last = min(page * per_page, total)

        msg = embed(f"Showing {first} to {last} of {total}", title="Browse Games")

        for g in query.from_self().limit(per_page).offset(offset).all():
            msg.add_field(
                name=g.pretty_name, value=", ".join(k.platform.title() for k in g.keys)
            )

        await ctx.send(embed=msg)
        
    @commands.command()
    async def random(self, ctx):
        """Display 20 random available games"""

        if not ctx.guild:
            await ctx.send(
                embed=embed(
                    f"This command should be sent in a guild. To see your keys use `{COMMAND_PREFIX}mykeys`"
                )
            )
            return

        session = Session()

        per_page = 20

        games, query = get_random_games(session, ctx.guild.id, per_page)

        total = query.count()

        msg = embed(f"Showing {min(20, total)} random games of {total} total", title="Random Games")

        for g, platforms in games.items():
            msg.add_field(name=g, value=", ".join(platforms.keys()))

        await ctx.send(embed=msg)

    @commands.command()
    async def share(self, ctx):
        """Add this guild the guilds you share keys with"""
        session = Session()

        member = Member.get(session, ctx.author.id, ctx.author.name)

        if ctx.guild:
            if ctx.guild.id in member.guilds:
                await ctx.send(
                    embed=embed(
                        f"You are already sharing with {ctx.guild.name}",
                        colour=Colours.GOLD,
                    )
                )
            else:
                member.guilds.append(ctx.guild.id)
                _, query = get_random_games(session, ctx.guild.id, 1)
                game_count = query.count()
                session.commit()
                await ctx.send(
                    embed=embed(
                        f"Thanks {ctx.author.name}! Your keys are now available on {ctx.guild.name}. There are now {game_count} games available.",
                        colour=Colours.GREEN,
                    )
                )
        else:
            await ctx.send(
                embed=embed(
                    f"You need to run this command in a guild. Not in a direct message",
                    colour=Colours.GOLD,
                )
            )

    @commands.command()
    async def unshare(self, ctx):
        """Remove this guild from the guilds you share keys with"""
        session = Session()
        member = Member.get(session, ctx.author.id, ctx.author.name)

        if ctx.guild:
            if ctx.guild.id not in member.guilds:
                await ctx.send(
                    embed=embed(
                        f"You aren't currently sharing with {ctx.guild.name}",
                        colour=Colours.GOLD,
                    )
                )
            else:
                member.guilds.remove(ctx.guild.id)
                _, query = get_random_games(session, ctx.guild.id, 1)
                game_count = query.count()
                session.commit()
                await ctx.send(
                    embed=embed(
                        f"Thanks {ctx.author.name}! You have removed {ctx.guild.name} from sharing. There are now {game_count} games available.",
                        colour=Colours.GREEN,
                    )
                )
        else:
            await ctx.send(
                embed=embed(
                    f"You need to run this command in a guild. Not in a direct message",
                    colour=Colours.RED,
                )
            )

    @commands.command()
    async def claim(self, ctx, platform, *game_name):
        """Claims a game from available keys"""
        session = Session()

        member = Member.get(session, ctx.author.id, ctx.author.name)
        ready, timeleft = claimable(member.last_claim)
        if not ready:
            await ctx.send(
                embed=embed(
                    f"You must wait {timeleft} until your next claim",
                    colour=Colours.RED,
                    title="Failed to claim",
                )
            )
            return

        if platform.lower() not in keyspace.keys():
            await ctx.send(
                embed=embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Failed to claim",
                )
            )
            return

        search_args = parse_name("_".join(game_name))

        if not await _validate_search_args(search_args, ctx):
            return

        games, _ = find_games(session, search_args, ctx.guild.id, 3)

        if len(games.keys()) > 1:
            msg = embed(
                "Please limit your search",
                title="Too many games found",
                colour=Colours.RED,
            )

            for g, platforms in games.items():
                msg.add_field(name=g, value=", ".join(platforms.keys()))

            await ctx.send(embed=msg)
            return

        if not games:
            await ctx.send(embed=embed("Game not found"))
            return

        game_name = list(games.keys())[0]
        key = games[game_name][platform][0]
        game = key.game

        msg = embed(
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
            embed=embed(
                f'"{game.pretty_name}" claimed by {ctx.user.name}. Check your PMs for more info. Enjoy!'
            )
        )


class DirectCommands(commands.Cog):
    """Run these commands in private messages to the bot"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def add(self, ctx, key, *game_name):
        """Add a key"""
        session = Session()

        pretty_name = " ".join(game_name)

        if not await _validate_search_args(pretty_name, ctx):
            return

        game = Game.get(session, pretty_name)

        platform, key = parse_key(key)

        if ctx.guild:
            try:
                await ctx.message.delete()
            except Exception:
                pass
            await ctx.author.send(
                embed=embed(
                    "You should really do this here, so it's only the bot giving away keys.",
                    colour=Colours.LUMINOUS_VIVID_PINK,
                )
            )

        if not platform:
            await ctx.send(embed=embed(key, Colours.RED))
            return

        found = session.query(Key).filter(Key.key == key).count()

        if found:
            await ctx.send(
                embed=embed(
                    f"Key already exists!",
                    Colours.GOLD,
                )
            )
            return

        member = Member.get(session, ctx.author.id, ctx.author.name)

        game.keys.append(Key(platform=platform, key=key, creator=member, game=game))

        session.commit()

        await ctx.author.send(
            embed=embed(
                f'Key for "{game.pretty_name}" added. Thanks {ctx.author.name}!',
                Colours.GREEN,
                title=f"{platform.title()} Key Added",
            )
        )

    @commands.command()
    async def remove(self, ctx, platform, *game_name):
        """Remove a key and send to you in a PM"""

        if platform not in keyspace.keys():
            await ctx.send(
                embed=embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search Error",
                )
            )
            return

        search_args = parse_name("_".join(game_name))

        if not await _validate_search_args(search_args, ctx):
            return

        session = Session()

        member = Member.get(session, ctx.author.id, ctx.author.name)

        query = (
            session.query(Game)
            .join(Key)
            .filter(
                Game.pretty_name.like(f"%{search_args}%"),
                Key.platform == platform,
                Key.creator_id == member.id,
            )
        )

        games = defaultdict(lambda: defaultdict(list))

        for g in query.from_self().all():
            games[g.pretty_name] = {
                k: list(v) for k, v in groupby(g.keys, lambda x: x.platform)
            }

        if len(games.keys()) > 1:
            msg = embed(
                "Please limit your search",
                title="Too many games found",
                colour=Colours.RED,
            )

            for g, platforms in games.items():
                msg.add_field(name=g, value=", ".join(platforms.keys()))

            await ctx.send(embed=msg)
            return

        if not games:
            await ctx.send(embed=embed("Game not found"))
            return

        game_name = list(games.keys())[0]
        key = games[game_name][platform][0]
        game = key.game

        msg = embed(
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
                embed=embed(f"This command needs to be sent in a direct message")
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

        msg = embed(f"Showing {first} to {last} of {total}")

        for k in query.limit(per_page).offset(offset).all():
            msg.add_field(name=f"{k.game.pretty_name}", value=f"{k.platform.title()}")

        await ctx.send(embed=msg)


bot.add_cog(GuildCommands(bot))
bot.add_cog(DirectCommands(bot))
