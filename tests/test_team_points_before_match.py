"""Tests for team_points_before_match -- the cumulative points-earned-
so-far ledger per team, scoped per competition."""


def test_points_before_match_starts_at_zero_and_accumulates(conn):
    """For every (team, competition) pair, the first match must show 0
    points accumulated, and every later match must equal the running
    sum of all prior points in that same competition."""
    pairs = conn.execute(
        "SELECT DISTINCT team_id, competition_id FROM team_points_before_match"
    ).fetchall()
    assert len(pairs) > 0

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