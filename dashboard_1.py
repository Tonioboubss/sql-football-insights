"""Interactive dashboard for the schedule-difficulty index -- pick a
team and see how difficult its calendar looks, match by match, broken
down by each of the 4 contributing factors."""

import sqlite3
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "football.db"

# Fixed categorical color order -- validated for colorblind-safe
# adjacent contrast in both light and dark mode. Never reassign a
# color to a different factor once a viewer has learned this mapping.
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


st.set_page_config(page_title="Schedule Difficulty", layout="centered")
st.title("Schedule Difficulty Index")

conn = get_connection()
teams = load_teams(conn)

team_name = st.selectbox("Team", teams["name"])
team_id = int(teams.loc[teams["name"] == team_name, "id"].iloc[0])

schedule = load_team_schedule(conn, team_id)

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