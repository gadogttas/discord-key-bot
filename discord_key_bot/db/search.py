from collections import defaultdict
from itertools import groupby

from discord_key_bot.db import func
from discord_key_bot.db.models import Game, Key, Member, Guild


def get_game_keys(session, game_name, guild_id):
    game = (
        session.query(Game)
        .join(Key)
        .filter(
            Key.creator_id.in_(
                session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id)
            )
        )
        .filter(Game.name == game_name)
        .first()
    )

    if game:
        return {
            k: list(v) for k, v in groupby(game.keys, lambda x: x.platform)
        }


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