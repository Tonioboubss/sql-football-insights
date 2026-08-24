CREATE VIEW IF NOT EXISTS team_match_results AS
    SELECT
        home_team_id AS team_id,
        competition_id,
        match_date,
        home_score AS goals_for,
        away_score AS goals_against,
        CASE
            WHEN home_score > away_score THEN 3
            WHEN home_score = away_score THEN 1
            ELSE 0
        END AS points
    FROM matches
    WHERE status IN ('FINISHED', 'AWARDED')

    UNION ALL

    SELECT
        away_team_id AS team_id,
        competition_id,
        match_date,
        away_score AS goals_for,
        home_score AS goals_against,
        CASE
            WHEN away_score > home_score THEN 3
            WHEN away_score = home_score THEN 1
            ELSE 0
        END AS points
    FROM matches
    WHERE status IN ('FINISHED', 'AWARDED');

CREATE VIEW IF NOT EXISTS team_points_before_match AS
    SELECT
        team_id,
        competition_id,
        match_date,
        points,
        COALESCE(
            SUM(points) OVER (
                PARTITION BY team_id, competition_id
                ORDER BY match_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ),
            0
        ) AS points_before_match
    FROM team_match_results;

CREATE VIEW IF NOT EXISTS team_rest_days AS
WITH team_match_dates AS (
    SELECT
        team_id,
        competition_id,
        match_date,
        LAG(match_date) OVER (
            PARTITION BY team_id ORDER BY match_date
        ) AS previous_match_date
    FROM team_match_results
)
SELECT
    team_id,
    competition_id,
    match_date,
    previous_match_date,
    julianday(match_date) - julianday(previous_match_date) AS rest_days
FROM team_match_dates;

-- Factor 1: recent form. Rolling average of points earned over the last
-- 5 matches (current match excluded). Same partitioning as
-- team_points_before_match, but with a bounded frame instead of an
-- unbounded one.
CREATE VIEW IF NOT EXISTS team_recent_form AS
SELECT
    team_id,
    competition_id,
    match_date,
    AVG(points) OVER (
        PARTITION BY team_id, competition_id
        ORDER BY match_date
        ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
    ) AS recent_form
FROM team_match_results;

-- Factor 2: team standing before the match, expressed as points per game
-- rather than an ordinal rank. Computing a true rank would require
-- comparing teams at the same point in time despite each playing on a
-- different match_date (games in hand) -- an "as of date" computation
-- out of scope for this MVP. Points per game is used as a continuous
-- proxy for current standing; a documented limitation, to be refined
-- into an accurate rank later.
CREATE VIEW IF NOT EXISTS team_standing_before_match AS
SELECT
    team_id,
    competition_id,
    match_date,
    points_before_match,
    ROW_NUMBER() OVER (
        PARTITION BY team_id, competition_id ORDER BY match_date
    ) - 1 AS games_played_before_match,
    CAST(points_before_match AS REAL) / NULLIF(
        ROW_NUMBER() OVER (PARTITION BY team_id, competition_id ORDER BY match_date) - 1,
        0
    ) AS points_per_game_before_match
FROM team_points_before_match;