"""Tests for team_opponent_factors -- the opponent-side join: for each
match, pulls in the SAME opponent's own row for the SAME match, so the
composite index can be computed from the opponent's perspective."""


def test_row_count_matches_team_match_factors(conn):
    """The self-join must produce exactly one opponent row per match
    row -- a wrong join key would fan out or drop rows silently."""
    base_count = conn.execute("SELECT COUNT(*) FROM team_match_factors").fetchone()[0]
    joined_count = conn.execute("SELECT COUNT(*) FROM team_opponent_factors").fetchone()[0]
    assert joined_count == base_count


def test_opponent_points_to_the_same_match_from_the_other_side(conn):
    """For a match where team A hosts team B, team B's row must report
    A as its own opponent, on the exact same match_date."""
    rows = conn.execute(
        "SELECT team_id, opponent_team_id, match_date FROM team_opponent_factors"
    ).fetchall()
    assert len(rows) > 0

    for team_id, opponent_team_id, match_date in rows:
        mirror = conn.execute(
            "SELECT opponent_team_id FROM team_match_factors WHERE team_id = ? AND match_date = ?",
            (opponent_team_id, match_date),
        ).fetchone()
        assert mirror is not None
        assert mirror[0] == team_id


def test_opponent_venue_form_reflects_the_venue_they_are_about_to_play(conn):
    """The opponent's venue_form must come from THEIR own perspective
    at the venue they are about to play -- always the opposite of the
    current team's venue for the same match."""
    rows = conn.execute(
        "SELECT team_id, opponent_team_id, competition_id, match_date, venue, opponent_venue_form "
        "FROM team_opponent_factors"
    ).fetchall()
    assert len(rows) > 0

    for team_id, opponent_team_id, competition_id, match_date, venue, opponent_venue_form in rows:
        opposite_venue = "AWAY" if venue == "HOME" else "HOME"
        expected = conn.execute(
            "SELECT venue_form_before_match FROM team_venue_form "
            "WHERE team_id = ? AND competition_id = ? AND venue = ? AND match_date = ?",
            (opponent_team_id, competition_id, opposite_venue, match_date),
        ).fetchone()[0]
        assert opponent_venue_form == expected