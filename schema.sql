CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY,
    external_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    code TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    external_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_competitions (
    team_id INTEGER NOT NULL REFERENCES teams(id),
    competition_id INTEGER NOT NULL REFERENCES competitions(id),
    PRIMARY KEY (team_id, competition_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    external_id INTEGER NOT NULL UNIQUE,
    competition_id INTEGER NOT NULL REFERENCES competitions(id),
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    match_date TEXT NOT NULL,       -- utcDate ISO 8601 from the API
    matchday INTEGER,                -- filled for league / group stage
    stage TEXT,                      -- filled for knockout rounds
    status TEXT NOT NULL CHECK (status IN (
        'SCHEDULED','TIMED','IN_PLAY','PAUSED','EXTRA_TIME',
        'PENALTY_SHOOTOUT','FINISHED','SUSPENDED','POSTPONED',
        'CANCELLED','AWARDED'
    )),
    home_score INTEGER,
    away_score INTEGER,
    CHECK (home_team_id <> away_team_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition_id);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);