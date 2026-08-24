"""Interactive dashboard for the schedule-difficulty index -- retrospective
analysis of how difficult each team's calendar was over the 2025-26 season,
broken down by each of the 4 contributing factors."""

import sqlite3
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "football.db"

FACTOR_COLORS = {
    "Recent form": "#2a78d6",
    "Standing": "#eb6834",
    "Venue form": "#1baf7a",
    "Rest days": "#eda100",
}
FACTOR_COLUMNS = {
    "normalized_recent_form": "Recent form",
    "normalized_standing": "Standing",
    "normalized_venue_form": "Venue form",
    "normalized_rest_days": "Rest days",
}
SELECTED_TEAM_COLOR = "#eb6834"  # slot 2 -- highlights the chosen team in the comparison chart
OTHER_TEAM_COLOR = "#2a78d6"     # slot 1 -- everyone else


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    """Streamlit re-runs the whole script on every user interaction --
    cache_resource keeps a single connection alive across reruns
    instead of reopening the database every time."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_teams(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT id, name FROM teams ORDER BY name", conn)


def load_team_schedule(conn: sqlite3.Connection, team_id: int) -> pd.DataFrame:
    query = """
        SELECT
            d.match_date,
            d.venue,
            t.name AS opponent,
            d.normalized_recent_form,
            d.normalized_standing,
            d.normalized_venue_form,
            d.normalized_rest_days,
            d.schedule_difficulty_index
        FROM team_schedule_difficulty d
        JOIN teams t ON t.id = d.opponent_team_id
        WHERE d.team_id = ?
        ORDER BY d.match_date
    """
    df = pd.read_sql_query(query, conn, params=(team_id,))
    df["match_date"] = pd.to_datetime(df["match_date"])
    return df


def load_season_ranking(conn: sqlite3.Connection) -> pd.DataFrame:
    """Average schedule-difficulty index per team, across the whole
    season and every competition that team played in -- answers "who
    had the hardest calendar overall?" rather than a single match."""
    query = """
        SELECT t.name AS team, AVG(d.schedule_difficulty_index) AS avg_difficulty
        FROM team_schedule_difficulty d
        JOIN teams t ON t.id = d.team_id
        WHERE d.schedule_difficulty_index IS NOT NULL
        GROUP BY t.id, t.name
        ORDER BY avg_difficulty DESC
    """
    return pd.read_sql_query(query, conn)


st.set_page_config(page_title="Schedule Difficulty", layout="centered")
st.title("Schedule Difficulty Index")
st.caption("Retrospective analysis -- 2025-26 season (Premier League, Ligue 1, Champions League)")

conn = get_connection()
teams = load_teams(conn)

tab_team, tab_season = st.tabs(["Team view", "Season comparison"])

with tab_team:
    team_name = st.selectbox("Team", teams["name"])
    team_id = int(teams.loc[teams["name"] == team_name, "id"].iloc[0])

    schedule = load_team_schedule(conn, team_id)
    valid_schedule = schedule.dropna(subset=["schedule_difficulty_index"])

    kpi_avg, kpi_hardest, kpi_easiest = st.columns(3)
    kpi_avg.metric("Average difficulty", f"{valid_schedule['schedule_difficulty_index'].mean():.2f}")

    if not valid_schedule.empty:
        hardest = valid_schedule.loc[valid_schedule["schedule_difficulty_index"].idxmax()]
        easiest = valid_schedule.loc[valid_schedule["schedule_difficulty_index"].idxmin()]
        kpi_hardest.metric(
            "Hardest match",
            f"vs {hardest['opponent']}",
            f"{hardest['schedule_difficulty_index']:.2f} -- {hardest['match_date'].date()}",
            delta_color="off",
        )
        kpi_easiest.metric(
            "Easiest match",
            f"vs {easiest['opponent']}",
            f"{easiest['schedule_difficulty_index']:.2f} -- {easiest['match_date'].date()}",
            delta_color="off",
        )

    st.subheader(f"{team_name} -- overall difficulty")
    headline_chart = (
        alt.Chart(schedule)
        .mark_line(strokeWidth=2, color=FACTOR_COLORS["Recent form"])
        .encode(
            x=alt.X("match_date:T", title="Match date"),
            y=alt.Y("schedule_difficulty_index:Q", title="Difficulty index (0-1)", scale=alt.Scale(domain=[0, 1])),
            tooltip=["match_date:T", alt.Tooltip("schedule_difficulty_index:Q", format=".2f")],
        )
        .properties(height=250)
    )
    st.altair_chart(headline_chart, use_container_width=True)

    st.subheader("Breakdown by factor")
    long_schedule = schedule.melt(
        id_vars=["match_date"],
        value_vars=list(FACTOR_COLUMNS.keys()),
        var_name="factor",
        value_name="value",
    )
    long_schedule["factor"] = long_schedule["factor"].map(FACTOR_COLUMNS)

    breakdown_chart = (
        alt.Chart(long_schedule)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("match_date:T", title="Match date"),
            y=alt.Y("value:Q", title="Normalized value (0-1)", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color(
                "factor:N",
                title="Factor",
                scale=alt.Scale(domain=list(FACTOR_COLORS.keys()), range=list(FACTOR_COLORS.values())),
            ),
            tooltip=["match_date:T", "factor:N", alt.Tooltip("value:Q", format=".2f")],
        )
        .properties(height=300)
    )
    st.altair_chart(breakdown_chart, use_container_width=True)

    st.subheader("Raw data")
    st.dataframe(schedule, use_container_width=True)

with tab_season:
    st.subheader("Who had the hardest calendar this season?")
    ranking = load_season_ranking(conn)
    ranking["highlight"] = ranking["team"].apply(
        lambda name: "Selected team" if name == team_name else "Other teams"
    )

    ranking_chart = (
        alt.Chart(ranking)
        .mark_bar()
        .encode(
            x=alt.X("avg_difficulty:Q", title="Average difficulty index (0-1)", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("team:N", title=None, sort="-x"),
            color=alt.Color(
                "highlight:N",
                title=None,
                scale=alt.Scale(
                    domain=["Selected team", "Other teams"],
                    range=[SELECTED_TEAM_COLOR, OTHER_TEAM_COLOR],
                ),
            ),
            tooltip=["team:N", alt.Tooltip("avg_difficulty:Q", format=".2f")],
        )
        .properties(height=max(300, len(ranking) * 18))
    )
    st.altair_chart(ranking_chart, use_container_width=True)