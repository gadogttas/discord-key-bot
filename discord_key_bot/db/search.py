import typing
from collections import OrderedDict
from typing import List

from sqlalchemy import text, or_, and_, func, exists
from sqlalchemy.ext.baked import Result
from sqlalchemy.orm import Session, Query, aliased

from discord_key_bot.common.constants import DEFAULT_PAGE_SIZE
from discord_key_bot.common.util import (
    GamePlatformCount,
    PlatformCount,
    get_search_name,
)
from discord_key_bot.db.models import (
    Game,
    Key,
    Member,
    Guild,
)
from discord_key_bot.db import queries
from discord_key_bot.db.queries import SortOrder, paginated_queries
from discord_key_bot.platform import get_platform, Platform


def get_game(
    session: Session,
    game_name: str,
    guild_id: int = 0,
    member_id: int = 0,
) -> typing.Optional[Game]:
    game: typing.Optional[Game] = (
        session.query(Game)
        .join(Key)
        .filter(
            and_(
                or_(
                    guild_id == 0,
                    Key.creator_id.in_(session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id))
                ),
                or_(
                    member_id == 0,
                    Key.creator_id == member_id
                ),
                Game.name == get_search_name(game_name)
            )
        )
        .first()
    )

    return game


def get_admin_games(
    session: Session,
    game_name: str,
    limit: int = DEFAULT_PAGE_SIZE,
) -> typing.Sequence[Game]:
    statement: Query[typing.Type[Game]] = (
        session.query(Game)
        .filter(
            Game.name.like(f"%{get_search_name(game_name)}%")
        ).limit(limit)
    )

    return session.scalars(statement).all()


def get_admin_members(session: Session) -> typing.Sequence[Member]:
    statement: Query[typing.Type[Member]] = (
        session.query(Member).filter(Member.is_admin)
    )

    return session.scalars(statement).all()


def get_expiring_keys(
    session: Session,
        guild_id: int = 0,
        platform: Platform = None,
        page: int = 1,
        per_page: int = DEFAULT_PAGE_SIZE,
) -> typing.Tuple[List[Key], int]:
    statement: Query[typing.Type[Key]] = (
        session.query(Key)
        .filter(
            and_(
                or_(
                    not guild_id,
                    Key.creator_id.in_(
                        session.query(Member.id).join(Guild).filter(Guild.guild_id == guild_id)
                    )
                ),
                or_(
                    not platform,
                    Key.platform == _platform_search_str(platform)
                ),
                Key.expiration > func.current_date()
            )
        )
    )

    count: int = statement.count()
    offset: int = (page - 1) * per_page

    keys: List[Key] = []
    for key in session.scalars(statement.order_by(Key.expiration.asc()).limit(per_page).offset(offset)):
        keys.append(key)

    return keys, count


def find_key(
    session: Session,
    key: str,
) -> Key:
    key_data: typing.Optional[Key] = (
        session.query(Key)
        .filter(
            Key.key == key
        )
        .first()
    )

    return key_data


def get_paginated_games(
    session: Session,
    guild_id: int = 0,
    member_id: int = 0,
    platform: Platform = None,
    title: str = "",
    page: int = 1,
    per_page: int = DEFAULT_PAGE_SIZE,
    sort: SortOrder = SortOrder.TITLE,
) -> List[GamePlatformCount]:

    # TODO: make a less hacky query building solution
    query: str = paginated_queries[sort]

    offset: int = (page - 1) * per_page

    results: Result = session.execute(
        text(query),
        {
            "guild_id": guild_id,
            "offset": offset,
            "per_page": per_page,
            "member_id": member_id,
            "platform": _platform_search_str(platform),
            "search_args": get_search_name(title),
        },
    )

    # group platform key counts by game while preserving sort order
    platform_game_dict: typing.OrderedDict[str, List[PlatformCount]] = OrderedDict()
    for game_name, platform_name, key_count in results:
        platform_count: PlatformCount = PlatformCount(
            get_platform(platform_name), key_count
        )

        if game_name in platform_game_dict.keys():
            platform_game_dict[game_name].append(platform_count)
        else:
            platform_game_dict[game_name] = [platform_count]

    # turn the OrderedDict into something easier to work with
    platform_games: List[GamePlatformCount] = [
        GamePlatformCount(game, platforms)
        for game, platforms in platform_game_dict.items()
    ]

    return platform_games


def count_games(
    session: Session,
    guild_id: int = 0,
    platform: Platform = None,
    member_id: int = 0
) -> int:
    results: Result = session.execute(
        text(queries.count_games),
        {
            "guild_id": guild_id,
            "member_id": member_id,
            "platform": _platform_search_str(platform)
        },
    )

    return results.first()[0]


def key_exists(session: Session, key: str) -> bool:
    return bool(find_key(session=session, key=key))


def delete_expired(session: Session) -> typing.Tuple[int, int]:
    deleted_keys: int = session.query(Key).filter(Key.expiration < func.current_date()).delete()

    game_alias = aliased(Game)
    deleted_games: int = session.query(Game).filter(
                    ~session.query(game_alias).join(Key).filter(Game.id == game_alias.id).exists()
                ).delete()

    return deleted_games, deleted_keys


def _platform_search_str(platform: Platform) -> str:
    return platform.search_name if platform else ''
