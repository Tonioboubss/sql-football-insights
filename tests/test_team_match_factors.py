"""Tests for team_match_factors -- combines the 4 raw schedule-
difficulty factors (still from each team's own point of view) into a
single row per team per match."""


def test_row_count_matches_team_match_results(conn):
    """Every match-perspective row must get exactly one factor row --
    a wrong join key would silently drop or duplicate rows instead of
    raising an error."""
    base_count = conn.execute("SELECT COUNT(*) FROM team_match_results").fetchone()[0]
    joined_count = conn.execute("SELECT COUNT(*) FROM team_match_factors").fetchone()[0]
    assert joined_count == base_count


def test_factors_match_their_source_views(conn):
    """Spot-check: the combined row's values must be identical to what
    each underlying per-factor view already reports for the same key,
    not just structurally present."""
    rows = conn.execute(
        """
        SELECT team_id, competition_id, match_date, venue,
               recent_form, points_per_game_before_match,
               venue_form_before_match, rest_days
        FROM team_match_factors
        LIMIT 50
        """
    ).fetchall()
    assert len(rows) > 0

    for team_id, competition_id, match_date, venue, recent_form, ppg, venue_form, rest_days in rows:
        expected_recent_form = conn.execute(
            "SELECT recent_form FROM team_recent_form WHERE team_id = ? AND competition_id = ? AND match_date = ?",
            (team_id, competition_id, match_date),
        ).fetchone()[0]
        expected_ppg = conn.execute(
            "SELECT points_per_game_before_match FROM team_standing_before_match "
            "WHERE team_id = ? AND competition_id = ? AND match_date = ?",
            (team_id, competition_id, match_date),
        ).fetchone()[0]
        expected_venue_form = conn.execute(
            "SELECT venue_form_before_match FROM team_venue_form "
            "WHERE team_id = ? AND competition_id = ? AND venue = ? AND match_date = ?",
            (team_id, competition_id, venue, match_date),
        ).fetchone()[0]
        expected_rest_days = conn.execute(
            "SELECT rest_days FROM team_rest_days WHERE team_id = ? AND match_date = ?",
            (team_id, match_date),
        ).fetchone()[0]

        assert recent_form == expected_recent_form
        assert ppg == expected_ppg
        assert venue_form == expected_venue_form
        assert rest_days == expected_rest_days