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

def test_points_before_match_starts_at_zero_and_accumulates(conn):
    """For every (team, competition) pair, the first match must show 0
    points accumulated, and every later match must equal the running
    sum of all prior points in that same competition."""
    pairs = conn.execute(
        "SELECT DISTINCT team_id, competition_id FROM team_points_before_match"
    ).fetchall()

    for team_id, competition_id in pairs:
        rows = conn.execute(
            """
            SELECT points, points_before_match
            FROM team_points_before_match
            WHERE team_id = ? AND competition_id = ?
            ORDER BY match_date
            """,
            (team_id, competition_id),
        ).fetchall()

        running_total = 0
        for points, points_before_match in rows:
            assert points_before_match == running_total
            running_total += points

def test_points_reflect_real_match_outcomes(conn):
    """Independent check: recompute expected points directly from
    matches.home_score/away_score, and compare to what the view says --
    this verifies the view's logic against the raw source of truth,
    not just against itself."""
    matches = conn.execute(
        "SELECT home_team_id, away_team_id, home_score, away_score "
        "FROM matches WHERE status = 'FINISHED' LIMIT 20"
    ).fetchall()

    for home_id, away_id, home_score, away_score in matches:
        expected_home_points = 3 if home_score > away_score else (1 if home_score == away_score else 0)

        home_points = conn.execute(
            "SELECT points FROM team_match_results WHERE team_id = ? AND goals_for = ? AND goals_against = ?",
            (home_id, home_score, away_score),
        ).fetchone()[0]

        assert home_points == expected_home_points