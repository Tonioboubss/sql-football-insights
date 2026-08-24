"""Tests for team_rest_days -- factor 4 of the schedule-difficulty
index: days of rest since the previous match, across ALL competitions
a team plays in."""

from datetime import datetime

import pytest


def test_rest_days_first_match_has_no_previous(conn):
    """A team's very first match (across ALL competitions) has no
    previous match, so rest_days must be NULL -- not zero, not negative."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT team_id, MIN(match_date) AS first_match_date
        FROM team_rest_days
        GROUP BY team_id
        """
    )
    first_matches = cur.fetchall()
    assert len(first_matches) > 0

    for team_id, first_match_date in first_matches:
        cur.execute(
            "SELECT rest_days FROM team_rest_days WHERE team_id = ? AND match_date = ?",
            (team_id, first_match_date),
        )
        rest_days = cur.fetchone()[0]
        assert rest_days is None


def test_rest_days_are_never_negative(conn):
    """A previous match can never fall after the current one (ORDER BY
    match_date guarantees this), so rest_days must always be >= 0."""
    cur = conn.cursor()
    cur.execute("SELECT rest_days FROM team_rest_days WHERE rest_days IS NOT NULL")
    values = [row[0] for row in cur.fetchall()]
    assert len(values) > 0
    assert all(value >= 0 for value in values)


def test_rest_days_matches_python_computation(conn):
    """Two independent implementations of the same logic must agree:
    the SQL LAG/julianday view vs. a plain Python diff between
    consecutive match dates, sorted per team across ALL competitions."""
    cur = conn.cursor()
    cur.execute(
        "SELECT team_id, match_date FROM team_match_results ORDER BY team_id, match_date"
    )
    rows = cur.fetchall()

    expected = {}
    previous_date_by_team = {}
    for team_id, match_date in rows:
        previous_date = previous_date_by_team.get(team_id)
        if previous_date is not None:
            current_dt = datetime.fromisoformat(match_date.replace("Z", "+00:00"))
            previous_dt = datetime.fromisoformat(previous_date.replace("Z", "+00:00"))
            expected[(team_id, match_date)] = (current_dt - previous_dt).total_seconds() / 86400
        previous_date_by_team[team_id] = match_date

    cur.execute(
        "SELECT team_id, match_date, rest_days FROM team_rest_days WHERE rest_days IS NOT NULL"
    )
    for team_id, match_date, rest_days in cur.fetchall():
        assert rest_days == pytest.approx(expected[(team_id, match_date)])


def test_rest_days_partition_spans_competitions(conn):
    """Guards the actual architectural decision: PARTITION BY team_id
    alone, not team_id + competition_id. There must be at least one
    case where the previous match belongs to a different competition
    than the current one."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.competition_id AS current_competition,
               p.competition_id AS previous_competition
        FROM team_rest_days r
        JOIN team_match_results p
          ON p.team_id = r.team_id AND p.match_date = r.previous_match_date
        WHERE r.previous_match_date IS NOT NULL
        """
    )
    rows = cur.fetchall()
    assert any(current != previous for current, previous in rows)