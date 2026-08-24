"""Tests for team_match_results -- the foundational reshape that turns
each match into two team-perspective rows (one per side), adding the
opponent's id, the venue played, and the points earned."""


def test_points_reflect_real_match_outcomes(conn):
    """Independent check: recompute the expected points directly from
    matches.home_score/away_score for both sides of every finished
    match, and compare to what the view stores -- this verifies the
    view's CASE logic against the raw source of truth, not against
    itself."""
    matches = conn.execute(
        "SELECT home_team_id, away_team_id, home_score, away_score "
        "FROM matches WHERE status IN ('FINISHED', 'AWARDED')"
    ).fetchall()
    assert len(matches) > 0

    for home_id, away_id, home_score, away_score in matches:
        expected_home_points = 3 if home_score > away_score else (1 if home_score == away_score else 0)
        expected_away_points = 3 if away_score > home_score else (1 if home_score == away_score else 0)

        home_points = conn.execute(
            "SELECT points FROM team_match_results WHERE team_id = ? AND venue = 'HOME' "
            "AND goals_for = ? AND goals_against = ?",
            (home_id, home_score, away_score),
        ).fetchone()[0]
        away_points = conn.execute(
            "SELECT points FROM team_match_results WHERE team_id = ? AND venue = 'AWAY' "
            "AND goals_for = ? AND goals_against = ?",
            (away_id, away_score, home_score),
        ).fetchone()[0]

        assert home_points == expected_home_points
        assert away_points == expected_away_points


def test_every_finished_match_produces_exactly_two_rows(conn):
    """The UNION ALL must double every finished/awarded match into
    exactly one HOME row and one AWAY row -- never more, never less."""
    match_count = conn.execute(
        "SELECT COUNT(*) FROM matches WHERE status IN ('FINISHED', 'AWARDED')"
    ).fetchone()[0]
    row_count = conn.execute("SELECT COUNT(*) FROM team_match_results").fetchone()[0]
    assert row_count == match_count * 2


def test_opponent_team_id_is_the_other_side_of_the_match(conn):
    """Each team-perspective row's opponent_team_id must point back to
    the actual other team of that same match."""
    rows = conn.execute(
        "SELECT team_id, opponent_team_id, venue, match_date FROM team_match_results"
    ).fetchall()
    assert len(rows) > 0

    for team_id, opponent_team_id, venue, match_date in rows:
        if venue == "HOME":
            match = conn.execute(
                "SELECT away_team_id FROM matches WHERE home_team_id = ? AND match_date = ?",
                (team_id, match_date),
            ).fetchone()
        else:
            match = conn.execute(
                "SELECT home_team_id FROM matches WHERE away_team_id = ? AND match_date = ?",
                (team_id, match_date),
            ).fetchone()
        assert match is not None
        assert opponent_team_id == match[0]