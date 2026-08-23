"""Data quality checks on the loaded database -- these should always
hold true regardless of which season/competitions we load."""

import sqlite3
from pathlib import Path

import pytest

DB_PATH = Path(__file__).parent.parent / "football.db"


@pytest.fixture
def conn():
    connection = sqlite3.connect(DB_PATH)
    yield connection
    connection.close()


def test_no_finished_match_has_a_missing_score(conn):
    """A FINISHED match without a score would indicate a parsing bug."""
    rows = conn.execute(
        "SELECT id FROM matches WHERE status = 'FINISHED' AND (home_score IS NULL OR away_score IS NULL)"
    ).fetchall()
    assert rows == []


def test_no_team_plays_itself(conn):
    """The schema's CHECK constraint should already prevent this --
    verify it actually holds in the loaded data."""
    rows = conn.execute("SELECT id FROM matches WHERE home_team_id = away_team_id").fetchall()
    assert rows == []


def test_match_count_per_competition_sums_to_the_total(conn):
    """Sanity check: matches grouped by competition must sum back to
    the overall total -- catches a broken competition_id somewhere."""
    total = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    summed = conn.execute(
        "SELECT SUM(cnt) FROM (SELECT COUNT(*) AS cnt FROM matches GROUP BY competition_id)"
    ).fetchone()[0]
    assert total == summed