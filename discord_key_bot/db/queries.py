from enum import Enum
from typing import Dict


class SortOrder(Enum):
    TITLE = 1
    LATEST = 2
    RANDOM = 3
    EXPIRATION = 4


_paginated_game_template: str = """
WITH platform_games AS (
    SELECT 
        games.id as game_id,
        games.pretty_name AS game_name, 
        keys.platform AS platform,
        IIF(:expiring_only = 1, keys.expiration, NULL) AS expiration,
        count(keys.id) AS key_count 
    FROM 
        games 
        JOIN keys 
            ON games.id = keys.game_id 
        JOIN members
            ON members.id = keys.creator_id
    WHERE 
        (:member_id = 0 OR members.id = :member_id)
        AND (:platform = '' OR keys.platform = :platform)
        AND (:search_args = '' OR games.name LIKE '%' || :search_args || '%')
        AND ((keys.expiration IS NULL AND :expiring_only = 0) OR keys.expiration > CURRENT_DATE)
        AND ( 
            :guild_id = 0 
            OR EXISTS (
                SELECT 1
                FROM guilds 
                WHERE 
                    members.id = guilds.member_id 
                    AND guilds.guild_id = :guild_id))
    GROUP BY 
        games.id, keys.platform
),
page AS (
    SELECT 
        DISTINCT game_id 
    FROM 
        platform_games 
    ORDER BY 
        {}
    LIMIT :per_page
    OFFSET :offset
)

SELECT 
    game_name, platform, expiration, key_count 
FROM 
    platform_games 
    JOIN page
        ON platform_games.game_id = page.game_id
    ORDER BY 
        {};
"""

paginated_queries: Dict[SortOrder, str] = {
    SortOrder.TITLE: _paginated_game_template.format(
        "LOWER(game_name) ASC", "LOWER(game_name) ASC"
    ),
    SortOrder.LATEST: _paginated_game_template.format(
        "game_id DESC", "platform_games.game_id DESC"
    ),
    SortOrder.RANDOM: _paginated_game_template.format(
        "RANDOM()", "LOWER(game_name) ASC"
    ),
    SortOrder.EXPIRATION: _paginated_game_template.format(
        "expiration ASC", "expiration ASC, LOWER(game_name) ASC"
    ),
}

count_games: str = """
    SELECT 
        COUNT(1)
    FROM 
        games
    WHERE EXISTS (
        SELECT 1
        FROM 
            keys 
            JOIN members
                ON members.id = keys.creator_id
        WHERE 
            keys.game_id = games.id
            AND (:member_id = 0 OR members.id = :member_id)
            AND (:platform = '' OR keys.platform = :platform)
            AND ((keys.expiration IS NULL AND :expiring_only = 0) OR keys.expiration > CURRENT_DATE)
            AND (
                :guild_id = 0 
                OR EXISTS (
                    SELECT 1
                    FROM guilds
                    WHERE 
                        members.id = guilds.member_id 
                        AND guilds.guild_id = :guild_id))
    )
"""
