"""Tests for team_schedule_difficulty -- the final composite index:
equal-weighted average of the 4 opponent-side factors, each min-max
normalized to [0, 1]."""

import pytest


def test_row_count_matches_team_opponent_factors(conn):
    """The CROSS JOIN against a single-row bounds CTE must not change
    the number of rows."""
    base_count = conn.execute("SELECT COUNT(*) FROM team_opponent_factors").fetchone()[0]
    result_count = conn.execute("SELECT COUNT(*) FROM team_schedule_difficulty").fetchone()[0]
    assert result_count == base_count


def test_index_is_within_the_normalized_range(conn):
    """An equal-weighted average of 4 values already normalized to
    [0, 1] can never fall outside that range."""
    values = [
        row[0]
        for row in conn.execute(
            "SELECT schedule_difficulty_index FROM team_schedule_difficulty "
            "WHERE schedule_difficulty_index IS NOT NULL"
        ).fetchall()
    ]
    assert len(values) > 0
    assert all(0 <= value <= 1 for value in values)


def test_index_matches_python_recomputation(conn):
    """Two independent implementations must agree: the SQL min-max
    normalization + average vs. the same formula recomputed in Python
    from team_opponent_factors and its own global min/max per column."""
    all_rows = conn.execute(
        """
        SELECT team_id, opponent_team_id, match_date,
               opponent_recent_form, opponent_standing,
               opponent_venue_form, opponent_rest_days
        FROM team_opponent_factors
        """
    ).fetchall()
    assert len(all_rows) > 0

    def bounds(column_index):
        values = [row[column_index] for row in all_rows if row[column_index] is not None]
        return min(values), max(values)

    min_form, max_form = bounds(3)
    min_standing, max_standing = bounds(4)
    min_venue, max_venue = bounds(5)
    min_rest, max_rest = bounds(6)

    complete_rows = [row for row in all_rows if all(value is not None for value in row[3:])]
    assert len(complete_rows) > 0

    for team_id, opponent_team_id, match_date, form, standing, venue_form, rest_days in complete_rows:
        expected = (
            (form - min_form) / (max_form - min_form)
            + (standing - min_standing) / (max_standing - min_standing)
            + (venue_form - min_venue) / (max_venue - min_venue)
            + (rest_days - min_rest) / (max_rest - min_rest)
        ) / 4.0

        actual = conn.execute(
            "SELECT schedule_difficulty_index FROM team_schedule_difficulty "
            "WHERE team_id = ? AND opponent_team_id = ? AND match_date = ?",
            (team_id, opponent_team_id, match_date),
        ).fetchone()[0]

        assert actual == pytest.approx(expected)