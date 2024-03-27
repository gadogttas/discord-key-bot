from datetime import datetime

from discord.ext import commands

from discord_key_bot.common import util
from discord_key_bot.db import Session, search
from discord_key_bot.db.models import Member
from discord_key_bot.keyparse import keyspace, parse_name, examples
from discord_key_bot.common.colours import Colours

class GuildCommands(commands.Cog):
    def __init__(self, bot, bot_channel_id, wait_time):
        self.bot = bot
        self.bot_channel_id = bot_channel_id
        self.wait_time = wait_time

    async def cog_before_invoke(self, ctx):
        if (self.bot_channel_id and str(ctx.channel.id) != self.bot_channel_id):
            raise commands.CommandError('wrong channel')

    @commands.command()
    async def search(self, ctx, *game_name):
        """Searches available games"""

        msg = util.embed("Top 15 search results...", title="Search Results")

        session = Session()

        search_args = parse_name("_".join(game_name))

        if not await util.validate_search_args(search_args, ctx):
            return

        games, _ = search.find_games(session, search_args, ctx.guild.id)

        for g, platforms in games.items():
            value = "\n".join(f"{p.title()}: {len(c)}" for p, c in platforms.items())
            msg.add_field(name=g, value=value, inline=True)

        await ctx.send(embed=msg)

    @commands.command()
    async def platforms(self, ctx):
        """Shows valid platforms"""

        msg = util.embed(f"Showing valid platforms and example key formats", title="Platforms")

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
                embed=util.embed(
                    f"This command should be sent in a guild. To see your keys use `{self.bot.command_prefix}mykeys`"
                )
            )
            return

        platform_lower = platform.lower()

        if platform_lower not in keyspace.keys():
            await ctx.send(
                embed=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Search failed",
                )
            )
            return

        session = Session()

        per_page = 20
        offset = (page - 1) * per_page

        games, query = search.find_games_by_platform(session, platform_lower, ctx.guild.id, per_page, offset)

        first = offset + 1
        total = query.count()
        last = min(page * per_page, total)

        msg = util.embed(f"Showing {first} to {last} of {total}", title=f"Browse Games available for {platform}")

        for g, count in games.items():
            value = f"Keys available: {count}"
            msg.add_field(name=g, value=value, inline=True)

        await ctx.send(embed=msg)

    @commands.command()
    async def browse(self, ctx, page=1):
        """Browse through available games"""

        if not ctx.guild:
            await ctx.send(
                embed=util.embed(
                    f"This command should be sent in a guild. To see your keys use `{self.bot.command_prefix}mykeys`"
                )
            )
            return

        session = Session()

        per_page = 20
        offset = (page - 1) * per_page

        games, query = search.find_games(session, "", ctx.guild.id, per_page, offset)

        first = offset + 1
        total = query.count()
        last = min(page * per_page, total)

        msg = util.embed(f"Showing {first} to {last} of {total}", title="Browse Games")

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
                embed=util.embed(
                    f"This command should be sent in a guild. To see your keys use `{self.bot.command_prefix}mykeys`"
                )
            )
            return

        session = Session()

        per_page = 20

        games, query = search.get_random_games(session, ctx.guild.id, per_page)

        total = query.count()

        msg = util.embed(f"Showing {min(20, total)} random games of {total} total", title="Random Games")

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
                    embed=util.embed(
                        f"You are already sharing with {ctx.guild.name}",
                        colour=Colours.GOLD,
                    )
                )
            else:
                member.guilds.append(ctx.guild.id)
                _, query = search.get_random_games(session, ctx.guild.id, 1)
                game_count = query.count()
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
    async def unshare(self, ctx):
        """Remove this guild from the guilds you share keys with"""
        session = Session()
        member = Member.get(session, ctx.author.id, ctx.author.name)

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
                _, query = search.get_random_games(session, ctx.guild.id, 1)
                game_count = query.count()
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
    async def claim(self, ctx, platform, *game_name):
        """Claims a game from available keys"""
        session = Session()

        member = Member.get(session, ctx.author.id, ctx.author.name)
        ready, timeleft = self.claimable(member.last_claim)
        if not ready:
            await ctx.send(
                embed=util.embed(
                    f"You must wait {timeleft} until your next claim",
                    colour=Colours.RED,
                    title="Failed to claim",
                )
            )
            return

        platform_lower = platform.lower()

        if platform_lower not in keyspace.keys():
            await ctx.send(
                embed=util.embed(
                    f'"{platform}" is not valid platform',
                    colour=Colours.RED,
                    title="Failed to claim",
                )
            )
            return

        search_args = parse_name("_".join(game_name))

        if not await util.validate_search_args(search_args, ctx):
            return

        game = search.get_game_keys(session, search_args, ctx.guild.id)

        if not game:
            await ctx.send(embed=util.embed("Game not found"))
            return

        key = game[platform_lower][0]
        game = key.game

        msg = util.embed(
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

    def claimable(self, timestamp):
        if timestamp:
            return (
                datetime.utcnow() - timestamp > self.wait_time,
                timestamp + self.wait_time - datetime.utcnow(),
            )
        else:
            return True, None