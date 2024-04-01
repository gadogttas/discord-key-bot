import typing
from collections import OrderedDict
from itertools import groupby
from typing import Dict, List

from sqlalchemy.ext.baked import Result
from sqlalchemy.orm import Session

from discord_key_bot.common.util import GamePlatformCount, PlatformCount, get_search_name
from discord_key_bot.db.models import Game, Key, Member, Guild
from discord_key_bot.db import queries
from discord_key_bot.db.queries import SortOrder, paginated_queries
from discord_key_bot.platform import all_platforms

DEFAULT_PAGE_SIZE: int = 15


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
        .filter(Game.name == get_search_name(game_name))
        .first()
    )

    key_dict: Dict[str, List[Key]] = {}

    if game:
        key_dict = {
            platform: list(keys)
            for platform, keys in groupby(game.keys, lambda x: x.platform)
        }

    return key_dict


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


def get_paginated_games(
    session: Session,
    guild_id: int = 0,
    member_id: int = 0,
    platform: str = "",
    title: str = "",
    page: int = 1,
    per_page: int = DEFAULT_PAGE_SIZE,
    sort: SortOrder = SortOrder.TITLE,
) -> List[GamePlatformCount]:

    # TODO: make a less hacky query building solution
    query: str = paginated_queries[sort]

    offset: int = (page - 1) * per_page

    results: Result = session.execute(
        query,
        {
            "guild_id": guild_id,
            "offset": offset,
            "per_page": per_page,
            "member_id": member_id,
            "platform": platform,
            "search_args": get_search_name(title),
        },
    )

    platform_game_dict: typing.OrderedDict[str, List[PlatformCount]] = OrderedDict()

    for game_name, platform_name, key_count in results:
        platform_count: PlatformCount = PlatformCount(
            all_platforms[platform_name], key_count
        )

        if game_name in platform_game_dict.keys():
            platform_game_dict[game_name].append(platform_count)
        else:
            platform_game_dict[game_name] = [platform_count]

    platform_games: List[GamePlatformCount] = [
        GamePlatformCount(game, platforms)
        for game, platforms in platform_game_dict.items()
    ]

    return platform_games


def count_games(
    session: Session, guild_id: int = 0, platform: str = "", member_id: int = 0
) -> int:
    results: Result = session.execute(
        queries.count_games,
        {"guild_id": guild_id, "member_id": member_id, "platform": platform},
    )

    return results.first()[0]


def key_exists(session: Session, key: str) -> bool:
    return bool(session.query(Key).filter(Key.key == key).count())


