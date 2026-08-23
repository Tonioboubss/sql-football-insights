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