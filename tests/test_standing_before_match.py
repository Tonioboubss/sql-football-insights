"""Tests for team_standing_before_match -- factor 2 of the schedule-
difficulty index, expressed as points per game rather than a rank
(documented MVP limitation -- see the architecture notes)."""

import pytest


def test_points_per_game_is_null_only_before_the_first_match(conn):
    """No games played yet means no points-per-game average -- and
    that must only ever be true for the very first match."""
    pairs = conn.execute(
        "SELECT DISTINCT team_id, competition_id FROM team_standing_before_match"
    ).fetchall()
    assert len(pairs) > 0

    for team_id, competition_id in pairs:
        rows = conn.execute(
            """
            SELECT games_played_before_match, points_per_game_before_match
            FROM team_standing_before_match
            WHERE team_id = ? AND competition_id = ?
            ORDER BY match_date
            """,
            (team_id, competition_id),
        ).fetchall()

        assert rows[0][0] == 0
        assert rows[0][1] is None
        assert all(games > 0 for games, _ in rows[1:])
        assert all(ppg is not None for _, ppg in rows[1:])


def test_points_per_game_equals_points_divided_by_games_played(conn):
    """Direct arithmetic check: points_per_game_before_match must equal
    points_before_match / games_played_before_match exactly."""
    rows = conn.execute(
        """
        SELECT points_before_match, games_played_before_match, points_per_game_before_match
        FROM team_standing_before_match
        WHERE games_played_before_match > 0
        """
    ).fetchall()
    assert len(rows) > 0

    for points_before_match, games_played, points_per_game in rows:
        assert points_per_game == pytest.approx(points_before_match / games_played)


def test_points_per_game_is_within_the_possible_points_range(conn):
    """An average of values in {0, 1, 3} can never fall outside [0, 3]."""
    values = [
        row[0]
        for row in conn.execute(
            "SELECT points_per_game_before_match FROM team_standing_before_match "
            "WHERE points_per_game_before_match IS NOT NULL"
        ).fetchall()
    ]
    assert len(values) > 0
    assert all(0 <= value <= 3 for value in values)