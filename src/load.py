"""Transform cached raw JSON into rows and load them into SQLite,
keeping only the fields our schema actually needs.

Load order matters: competitions and teams must exist before matches
can reference them via foreign keys.
"""

import json
import sqlite3
from pathlib import Path

from config import COMPETITIONS

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


def load_teams(conn: sqlite3.Connection) -> None:
    """Load every team that appears in any of our 3 competitions."""
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
    conn.commit()

def get_competition_id(conn: sqlite3.Connection, external_id: int) -> int:
    row = conn.execute("SELECT id FROM competitions WHERE external_id = ?", (external_id,)).fetchone()
    return row[0]


def get_team_id(conn: sqlite3.Connection, external_id: int) -> int:
    row = conn.execute("SELECT id FROM teams WHERE external_id = ?", (external_id,)).fetchone()
    return row[0]


def load_team_competitions(conn: sqlite3.Connection) -> None:
    """Link each team to every competition it played in this season."""
    for code in COMPETITIONS:
        competition_data = json.loads((RAW_DIR / f"{code}_competition.json").read_text())
        competition_id = get_competition_id(conn, competition_data["id"])

        teams_data = json.loads((RAW_DIR / f"{code}_teams.json").read_text())
        for team in teams_data["teams"]:
            team_id = get_team_id(conn, team["id"])
            conn.execute(
                "INSERT OR IGNORE INTO team_competitions (team_id, competition_id) VALUES (?, ?)",
                (team_id, competition_id),
            )
    conn.commit()

def load_matches(conn: sqlite3.Connection) -> None:
    """Load every match from all 3 competitions."""
    for code in COMPETITIONS:
        competition_data = json.loads((RAW_DIR / f"{code}_competition.json").read_text())
        competition_id = get_competition_id(conn, competition_data["id"])

        matches_data = json.loads((RAW_DIR / f"{code}_matches.json").read_text())
        for match in matches_data["matches"]:
            home_team_id = get_team_id(conn, match["homeTeam"]["id"])
            away_team_id = get_team_id(conn, match["awayTeam"]["id"])

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
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "match_date": match["utcDate"],
                    "matchday": match["matchday"],
                    "stage": match["stage"],
                    "status": match["status"],
                    "home_score": match["score"]["fullTime"]["home"],
                    "away_score": match["score"]["fullTime"]["away"],
                },
            )
    conn.commit()

def main() -> None:
    conn = get_connection()
    load_competitions(conn)
    load_teams(conn)
    load_team_competitions(conn)
    load_matches(conn)

    
    conn.close()

if __name__ == "__main__":
    main()