_paginated_game_template: str = """
WITH platform_games AS (
    SELECT 
        games.id as game_id,
        games.pretty_name AS game_name, 
        keys.platform AS platform, 
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
        AND EXISTS (
            SELECT 1
            FROM guilds 
            WHERE 
                members.id = guilds.member_id 
                AND (:guild_id = 0 OR guilds.guild_id = :guild_id)
        )
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
    game_name, platform, key_count 
FROM 
    platform_games 
    JOIN page
        ON platform_games.game_id = page.game_id
    ORDER BY 
        LOWER(game_name) ASC;
"""

games_paginated_by_title: str = _paginated_game_template.format("LOWER(game_name) ASC")
games_paginated_by_random: str = _paginated_game_template.format("RANDOM()")

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
            JOIN guilds 
                ON members.id = guilds.member_id 
        WHERE 
            keys.game_id = games.id
            AND (:member_id = 0 OR members.id = :member_id)
            AND (:platform = '' OR keys.platform = :platform)
            AND (:guild_id = 0 OR guilds.guild_id = :guild_id)
    )
"""
