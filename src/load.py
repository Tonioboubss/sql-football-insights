"""Transform cached raw JSON into rows and load them into SQLite,
keeping only the fields our schema actually needs.

Load order matters: competitions and teams must exist before matches
can reference them via foreign keys.

Assumption, verified against the current dataset: every match in the
cached JSON has a fully populated score.fullTime (home/away), because
the 2025-26 season is entirely finished (no SCHEDULED/POSTPONED
matches). Loading a season still in progress would need this
re-checked -- see the "Perspectives" section of the README.
"""

import json
import logging
import sqlite3
from pathlib import Path

from config import COMPETITIONS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
DB_PATH = Path(__file__).parent.parent / "football.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"
VIEWS_PATH = Path(__file__).parent.parent / "sql" / "views.sql"


def get_connection() -> sqlite3.Connection:
    """Open the database connection and make sure the schema exists."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores FK constraints unless told to enforce them
    conn.executescript(SCHEMA_PATH.read_text())
    conn.executescript(VIEWS_PATH.read_text())
    return conn


def load_competitions(conn: sqlite3.Connection) -> None:
    """Load each competition's metadata, discarding everything else (crests, area, etc.)."""
    for code in COMPETITIONS:
        data = json.loads((RAW_DIR / f"{code}_competition.json").read_text())
        conn.execute(
            """
            INSERT INTO competitions (external_id, name, code)
            VALUES (:external_id, :name, :code)
            ON CONFLICT (external_id) DO UPDATE SET
                name = excluded.name,
                code = excluded.code
            """,
            {"external_id": data["id"], "name": data["name"], "code": data["code"]},
        )
    conn.commit()
    logger.info("Loaded %d competitions", len(COMPETITIONS))


def load_teams(conn: sqlite3.Connection) -> None:
    """Load every team that appears in any of our 3 competitions."""
    total = 0
    for code in COMPETITIONS:
        data = json.loads((RAW_DIR / f"{code}_teams.json").read_text())
        for team in data["teams"]:
            conn.execute(
                """
                INSERT INTO teams (external_id, name)
                VALUES (:external_id, :name)
                ON CONFLICT (external_id) DO UPDATE SET name = excluded.name
                """,
                {"external_id": team["id"], "name": team["name"]},
            )
            total += 1
    conn.commit()
    logger.info("Loaded %d teams across %d competitions", total, len(COMPETITIONS))


def get_competition_id_map(conn: sqlite3.Connection) -> dict[int, int]:
    """Build an in-memory external_id -> internal_id lookup for
    competitions with a single query, instead of one SELECT per row in
    the loops below (classic N+1 query anti-pattern otherwise)."""
    rows = conn.execute("SELECT external_id, id FROM competitions").fetchall()
    return dict(rows)


def get_team_id_map(conn: sqlite3.Connection) -> dict[int, int]:
    """Same idea as get_competition_id_map, for teams."""
    rows = conn.execute("SELECT external_id, id FROM teams").fetchall()
    return dict(rows)


def load_team_competitions(conn: sqlite3.Connection) -> None:
    """Link each team to every competition it played in this season."""
    competition_ids = get_competition_id_map(conn)
    team_ids = get_team_id_map(conn)

    for code in COMPETITIONS:
        competition_data = json.loads((RAW_DIR / f"{code}_competition.json").read_text())
        competition_id = competition_ids[competition_data["id"]]

        teams_data = json.loads((RAW_DIR / f"{code}_teams.json").read_text())
        for team in teams_data["teams"]:
            external_id = team["id"]
            if external_id not in team_ids:
                raise ValueError(
                    f"Team external_id={external_id} ({team['name']}) not found in the "
                    f"database -- did load_teams() run first?"
                )
            conn.execute(
                "INSERT OR IGNORE INTO team_competitions (team_id, competition_id) VALUES (?, ?)",
                (team_ids[external_id], competition_id),
            )
    conn.commit()
    logger.info("Loaded team-competition links for %d competitions", len(COMPETITIONS))


def load_matches(conn: sqlite3.Connection) -> None:
    """Load every match from all 3 competitions."""
    competition_ids = get_competition_id_map(conn)
    team_ids = get_team_id_map(conn)
    total = 0

    for code in COMPETITIONS:
        competition_data = json.loads((RAW_DIR / f"{code}_competition.json").read_text())
        competition_id = competition_ids[competition_data["id"]]

        matches_data = json.loads((RAW_DIR / f"{code}_matches.json").read_text())
        logger.info("Loading %d matches for %s", len(matches_data["matches"]), code)

        for match in matches_data["matches"]:
            home_external_id = match["homeTeam"]["id"]
            away_external_id = match["awayTeam"]["id"]

            for external_id, side in ((home_external_id, "home"), (away_external_id, "away")):
                if external_id not in team_ids:
                    raise ValueError(
                        f"{side} team external_id={external_id} for match {match['id']} not "
                        f"found in the database -- was this team's roster loaded for this season?"
                    )

            conn.execute(
                """
                INSERT INTO matches (
                    external_id, competition_id, home_team_id, away_team_id,
                    match_date, matchday, stage, status, home_score, away_score
                )
                VALUES (
                    :external_id, :competition_id, :home_team_id, :away_team_id,
                    :match_date, :matchday, :stage, :status, :home_score, :away_score
                )
                ON CONFLICT (external_id) DO UPDATE SET
                    status = excluded.status,
                    home_score = excluded.home_score,
                    away_score = excluded.away_score
                """,
                {
                    "external_id": match["id"],
                    "competition_id": competition_id,
                    "home_team_id": team_ids[home_external_id],
                    "away_team_id": team_ids[away_external_id],
                    "match_date": match["utcDate"],
                    "matchday": match["matchday"],
                    "stage": match["stage"],
                    "status": match["status"],
                    "home_score": match["score"]["fullTime"]["home"],
                    "away_score": match["score"]["fullTime"]["away"],
                },
            )
            total += 1
    conn.commit()
    logger.info("Loaded %d matches across %d competitions", total, len(COMPETITIONS))


def main() -> None:
    conn = get_connection()
    try:
        load_competitions(conn)
        load_teams(conn)
        load_team_competitions(conn)
        load_matches(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()