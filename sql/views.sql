-- Views hold no data of their own -- only a stored query -- so dropping
-- and recreating them on every run is safe and keeps re-runs idempotent
-- AND up to date, unlike CREATE VIEW IF NOT EXISTS which silently keeps
-- a stale definition once a view already exists.

-- Reshapes matches into one row per team per match (team's own
-- perspective), across ALL competitions, adding the opponent's id and
-- the venue (HOME/AWAY) this team played at.
DROP VIEW IF EXISTS team_match_results;
CREATE VIEW team_match_results AS
    SELECT
        home_team_id AS team_id,
        away_team_id AS opponent_team_id,
        competition_id,
        match_date,
        'HOME' AS venue,
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
        home_team_id AS opponent_team_id,
        competition_id,
        match_date,
        'AWAY' AS venue,
        away_score AS goals_for,
        home_score AS goals_against,
        CASE
            WHEN away_score > home_score THEN 3
            WHEN away_score = home_score THEN 1
            ELSE 0
        END AS points
    FROM matches
    WHERE status IN ('FINISHED', 'AWARDED');


-- Cumulative points earned before each match, per competition.
DROP VIEW IF EXISTS team_points_before_match;
CREATE VIEW team_points_before_match AS
SELECT
    team_id,
    competition_id,
    match_date,
    points,
    COALESCE(SUM(points) OVER (
        PARTITION BY team_id, competition_id
        ORDER BY match_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ), 0) AS points_before_match
FROM team_match_results;


-- Factor 1: recent form. Rolling average of points earned over the
-- last 5 matches (current match excluded).
DROP VIEW IF EXISTS team_recent_form;
CREATE VIEW team_recent_form AS
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


-- Factor 2: team standing before the match, expressed as points per
-- game rather than an ordinal rank (documented MVP limitation -- see
-- the architecture notes).
DROP VIEW IF EXISTS team_standing_before_match;
CREATE VIEW team_standing_before_match AS
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


-- Factor 3: venue-specific strength. Average points earned in previous
-- matches played at the same venue (HOME or AWAY), excluding the
-- current match.
DROP VIEW IF EXISTS team_venue_form;
CREATE VIEW team_venue_form AS
SELECT
    team_id,
    competition_id,
    venue,
    match_date,
    AVG(points) OVER (
        PARTITION BY team_id, competition_id, venue
        ORDER BY match_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS venue_form_before_match
FROM team_match_results;


-- Factor 4: physical freshness. Days of rest since the previous match,
-- across ALL competitions (PARTITION BY team_id only).
DROP VIEW IF EXISTS team_rest_days;
CREATE VIEW team_rest_days AS
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


-- Combines the 4 raw factors -- still from each team's own point of
-- view -- into a single row per team per match.
DROP VIEW IF EXISTS team_match_factors;
CREATE VIEW team_match_factors AS
SELECT
    r.team_id,
    r.opponent_team_id,
    r.competition_id,
    r.match_date,
    r.venue,
    f.recent_form,
    s.points_per_game_before_match,
    v.venue_form_before_match,
    d.rest_days
FROM team_match_results r
JOIN team_recent_form f
  ON f.team_id = r.team_id AND f.competition_id = r.competition_id AND f.match_date = r.match_date
JOIN team_standing_before_match s
  ON s.team_id = r.team_id AND s.competition_id = r.competition_id AND s.match_date = r.match_date
JOIN team_venue_form v
  ON v.team_id = r.team_id AND v.competition_id = r.competition_id AND v.venue = r.venue AND v.match_date = r.match_date
JOIN team_rest_days d
  ON d.team_id = r.team_id AND d.match_date = r.match_date;


-- Opponent-side join: pulls in the opponent's own row for the same
-- match (both perspectives share the same match_date). Because one
-- team's HOME row always pairs with the other team's AWAY row,
-- opponent.venue_form automatically reflects the opponent's form at
-- the venue they are about to play at.
DROP VIEW IF EXISTS team_opponent_factors;
CREATE VIEW team_opponent_factors AS
SELECT
    m.team_id,
    m.opponent_team_id,
    m.competition_id,
    m.match_date,
    m.venue,
    o.recent_form AS opponent_recent_form,
    o.points_per_game_before_match AS opponent_standing,
    o.venue_form_before_match AS opponent_venue_form,
    o.rest_days AS opponent_rest_days
FROM team_match_factors m
JOIN team_match_factors o
  ON o.team_id = m.opponent_team_id
 AND o.match_date = m.match_date;


-- Composite schedule-difficulty index: equal-weighted average of the
-- 4 opponent-side factors, each min-max normalized to [0, 1] across
-- the full dataset so raw scales (days vs. points per game) don't
-- distort the average.
DROP VIEW IF EXISTS team_schedule_difficulty;
CREATE VIEW team_schedule_difficulty AS
WITH bounds AS (
    SELECT
        MIN(opponent_recent_form) AS min_form, MAX(opponent_recent_form) AS max_form,
        MIN(opponent_standing) AS min_standing, MAX(opponent_standing) AS max_standing,
        MIN(opponent_venue_form) AS min_venue, MAX(opponent_venue_form) AS max_venue,
        MIN(opponent_rest_days) AS min_rest, MAX(opponent_rest_days) AS max_rest
    FROM team_opponent_factors
)
SELECT
    t.team_id,
    t.opponent_team_id,
    t.competition_id,
    t.match_date,
    t.venue,
    (
        (t.opponent_recent_form - b.min_form) / NULLIF(b.max_form - b.min_form, 0)
      + (t.opponent_standing - b.min_standing) / NULLIF(b.max_standing - b.min_standing, 0)
      + (t.opponent_venue_form - b.min_venue) / NULLIF(b.max_venue - b.min_venue, 0)
      + (t.opponent_rest_days - b.min_rest) / NULLIF(b.max_rest - b.min_rest, 0)
    ) / 4.0 AS schedule_difficulty_index
FROM team_opponent_factors t
CROSS JOIN bounds b;