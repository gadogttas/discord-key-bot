import collections
import datetime
import typing
from typing import List

from sqlalchemy import text, or_, and_, func, exists
from sqlalchemy.ext.baked import Result
from sqlalchemy.orm import Session, Query, aliased

from discord_key_bot.common.defaults import PAGE_SIZE
from discord_key_bot.common.util import (
    GameKeyCount,
    KeyCount,
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
    limit: int = PAGE_SIZE,
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
    per_page: int = PAGE_SIZE,
    sort: SortOrder = SortOrder.TITLE,
    expiring_only: bool = False,
) -> List[List[GameKeyCount]]:
    # TODO: make a less hacky query building solution
    query: str = paginated_queries[sort]

    results: Result = session.execute(
        text(query),
        {
            "guild_id": guild_id,
            "member_id": member_id,
            "platform": _platform_search_str(platform),
            "search_args": get_search_name(title),
            "expiring_only": expiring_only
        },
    )

    # group platform key counts by game
    game_count_dict: typing.DefaultDict[str, List[KeyCount]] = collections.defaultdict(list)
    for game_name, platform_name, expiration, key_count in results:
        label: str = _get_key_count_label(platform_name, expiration)
        game_count_dict[game_name].append(KeyCount(label, key_count))

    # turn the dict into something easier to work with
    game_counts: List[GameKeyCount] = [
        GameKeyCount(game, platforms) for game, platforms in game_count_dict.items()
    ]

    return _get_pages(game_counts, sort, per_page)


def count_games(
    session: Session,
    guild_id: int = 0,
    platform: Platform = None,
    member_id: int = 0,
    expiring_only: bool = False,
) -> int:
    results: Result = session.execute(
        text(queries.count_games),
        {
            "guild_id": guild_id,
            "member_id": member_id,
            "platform": _platform_search_str(platform),
            "expiring_only": expiring_only,
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


def _get_key_count_label(platform_name: str, expiration: str) -> str:
    if expiration:
        # for whatever reason SQLAlchemy doesn't preserve the Datetime type on custom queries
        expiration_dt: datetime.datetime = datetime.datetime.strptime(expiration, "%Y-%m-%d %H:%M:%S.%f")
        expiration_str: str = datetime.datetime.strftime(expiration_dt, "%b %d %Y")
        return f"{get_platform(platform_name).name} ({expiration_str})"
    else:
        return get_platform(platform_name).name


def _get_pages(games: List[GameKeyCount], sort: SortOrder, page_size: int) -> List[List[GameKeyCount]]:
    pages: List[List[GameKeyCount]] = []
    for i in range(0, len(games), page_size):
        page: List[GameKeyCount] = games[i:i + page_size]

        if sort == SortOrder.RANDOM:
            list.sort(page, key=lambda game: game.name)

        pages.append(page)

    return pages
