from collections import defaultdict
from itertools import groupby
from typing import Tuple, Dict, List

from sqlalchemy.orm import Query

from discord_key_bot.db import func, Session
from discord_key_bot.db.models import Game, Key, Member, Guild
from discord_key_bot.platform import pretty_platform

DEFAULT_LIMIT: int = 15


def get_game_keys(
    session: Session, game_name: str, guild_id: int
) -> Dict[str, List[Key]]:
    game: Game = (
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

    key_dict: Dict[str, List[Key]] = {}

    if game:
        key_dict = {
            platform: list(keys)
            for platform, keys in groupby(game.keys, lambda x: x.platform)
        }

    return key_dict


def find_games(
    session: Session,
    search_args: str,
    guild_id: int,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> Tuple[Dict[Game, Dict[str, List[str]]], int]:
    query: Query = (
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

    count: int = query.count()

    if offset:
        result = query.from_self().limit(limit).offset(offset).all()
    else:
        result = query.from_self().limit(limit).all()

    games: Dict[Game, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for game in result:
        games[game] = {
            platform: list(keys)
            for platform, keys in groupby(game.keys, lambda x: x.platform)
        }

    return games, count


def get_random_games(
    session: Session, guild_id: int, limit: int = DEFAULT_LIMIT
) -> Tuple[Dict[str, Dict[str, List[str]]], int]:
    query: Query = (
        session.query(Game)
        .join(Key)
        .filter(
            Key.creator_id.in_(
                session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id)
            )
        )
        .order_by(func.random())
    )

    count: int = query.count()

    games: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

    for game in query.from_self().limit(limit).all():
        games[game.pretty_name] = {
            platform: list(keys)
            for platform, keys in groupby(game.keys, lambda x: x.platform)
        }

    return games, count


def game_count_by_platform(
    session: Session, platform, guild_id, limit=DEFAULT_LIMIT, offset=None
) -> Tuple[Dict[str, int], int]:
    query: Query = (
        session.query(Game.pretty_name, func.count(Game.pretty_name).label("count"))
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

    count: int = query.count()

    games: Dict[str, int] = {}

    for game in query.from_self().offset(offset).limit(limit).all():
        games[game.pretty_name] = game.count

    return games, count


def find_game_keys_for_user(
    session: Session, member: Member, platform: str, search_args: str
) -> Dict[str, List[Key]]:
    game: Game = (
        session.query(Game)
        .join(Key)
        .filter(
            Game.name == search_args,
            Key.platform == platform.lower(),
            Key.creator_id == member.id,
        )
        .first()
    )

    game_dict: Dict[str, List[Key]] = {}
    if game:
        game_dict = {
            platform: list(keys)
            for platform, keys in groupby(game.keys, lambda x: x.platform)
        }

    return game_dict


def find_user_games(
    session: Session, member: Member, offset: int = 1, per_page: int = 15
) -> Tuple[Dict[str, str], int]:
    query: Query = (
        session.query(Key)
        .join(Game)
        .filter(Key.creator_id == member.id)
        .order_by(Game.pretty_name.asc(), Key.platform.asc())
    )

    count: int = query.count()

    platform_games: Dict[str, str] = {}

    for game in query.limit(per_page).offset(offset).all():
        platform_games[game.game.pretty_name] = pretty_platform(game.platform)

    return platform_games, count
