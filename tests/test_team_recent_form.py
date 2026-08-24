"""Tests for team_recent_form -- factor 1 of the schedule-difficulty
index: a team's average points over its last 5 matches, ignoring the
current one."""

import pytest


def test_recent_form_is_null_only_for_the_very_first_match(conn):
    """With no prior matches to average, recent_form must be NULL --
    and only for the first match of each (team, competition) pair."""
    pairs = conn.execute(
        "SELECT DISTINCT team_id, competition_id FROM team_recent_form"
    ).fetchall()
    assert len(pairs) > 0

    for team_id, competition_id in pairs:
        rows = conn.execute(
            """
            SELECT recent_form
            FROM team_recent_form
            WHERE team_id = ? AND competition_id = ?
            ORDER BY match_date
            """,
            (team_id, competition_id),
        ).fetchall()

        assert rows[0][0] is None
        assert all(recent_form is not None for (recent_form,) in rows[1:])


def test_recent_form_matches_python_computation(conn):
    """Two independent implementations must agree: the SQL rolling
    window vs. a plain Python average of the last up-to-5 points."""
    pairs = conn.execute(
        "SELECT DISTINCT team_id, competition_id FROM team_match_results"
    ).fetchall()

    for team_id, competition_id in pairs:
        rows = conn.execute(
            """
            SELECT match_date, points
            FROM team_match_results
            WHERE team_id = ? AND competition_id = ?
            ORDER BY match_date
            """,
            (team_id, competition_id),
        ).fetchall()

        history = []
        for match_date, points in rows:
            if history:
                window = history[-5:]
                expected = sum(window) / len(window)
                actual = conn.execute(
                    "SELECT recent_form FROM team_recent_form "
                    "WHERE team_id = ? AND competition_id = ? AND match_date = ?",
                    (team_id, competition_id, match_date),
                ).fetchone()[0]
                assert actual == pytest.approx(expected)
            history.append(points)


def test_recent_form_is_within_the_possible_points_range(conn):
    """An average of values in {0, 1, 3} can never fall outside [0, 3]."""
    values = [
        row[0]
        for row in conn.execute(
            "SELECT recent_form FROM team_recent_form WHERE recent_form IS NOT NULL"
        ).fetchall()
    ]
    assert len(values) > 0
    assert all(0 <= value <= 3 for value in values)