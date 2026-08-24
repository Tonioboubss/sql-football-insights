"""Tests for team_venue_form -- factor 3 of the schedule-difficulty
index: a team's average points at a given venue (HOME or AWAY) prior
to the current match, computed separately per venue."""

import pytest


def test_venue_form_is_null_only_for_the_first_match_at_that_venue(conn):
    """A team's first HOME match (and, separately, its first AWAY
    match) has no prior history at that venue, so venue_form_before_match
    must be NULL only there."""
    groups = conn.execute(
        "SELECT DISTINCT team_id, competition_id, venue FROM team_venue_form"
    ).fetchall()
    assert len(groups) > 0

    for team_id, competition_id, venue in groups:
        rows = conn.execute(
            """
            SELECT venue_form_before_match
            FROM team_venue_form
            WHERE team_id = ? AND competition_id = ? AND venue = ?
            ORDER BY match_date
            """,
            (team_id, competition_id, venue),
        ).fetchall()

        assert rows[0][0] is None
        assert all(value is not None for (value,) in rows[1:])


def test_venue_form_matches_python_computation(conn):
    """Two independent implementations must agree: the SQL cumulative
    average per venue vs. a plain Python running average, computed
    separately for HOME and AWAY matches."""
    groups = conn.execute(
        "SELECT DISTINCT team_id, competition_id, venue FROM team_match_results"
    ).fetchall()

    for team_id, competition_id, venue in groups:
        rows = conn.execute(
            """
            SELECT match_date, points
            FROM team_match_results
            WHERE team_id = ? AND competition_id = ? AND venue = ?
            ORDER BY match_date
            """,
            (team_id, competition_id, venue),
        ).fetchall()

        history = []
        for match_date, points in rows:
            if history:
                expected = sum(history) / len(history)
                actual = conn.execute(
                    "SELECT venue_form_before_match FROM team_venue_form "
                    "WHERE team_id = ? AND competition_id = ? AND venue = ? AND match_date = ?",
                    (team_id, competition_id, venue, match_date),
                ).fetchone()[0]
                assert actual == pytest.approx(expected)
            history.append(points)


def test_venue_form_is_within_the_possible_points_range(conn):
    """An average of values in {0, 1, 3} can never fall outside [0, 3]."""
    values = [
        row[0]
        for row in conn.execute(
            "SELECT venue_form_before_match FROM team_venue_form WHERE venue_form_before_match IS NOT NULL"
        ).fetchall()
    ]
    assert len(values) > 0
    assert all(0 <= value <= 3 for value in values)