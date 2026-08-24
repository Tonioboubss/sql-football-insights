"""Interactive dashboard for the schedule-difficulty index -- pick a
team and see how difficult its calendar looks, match by match."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "football.db"


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
            d.schedule_difficulty_index
        FROM team_schedule_difficulty d
        JOIN teams t ON t.id = d.opponent_team_id
        WHERE d.team_id = ?
        ORDER BY d.match_date
    """
    return pd.read_sql_query(query, conn, params=(team_id,))


st.set_page_config(page_title="Schedule Difficulty", layout="centered")
st.title("Schedule Difficulty Index")

conn = get_connection()
teams = load_teams(conn)

team_name = st.selectbox("Team", teams["name"])
team_id = int(teams.loc[teams["name"] == team_name, "id"].iloc[0])

schedule = load_team_schedule(conn, team_id)

st.subheader(f"{team_name} -- match-by-match difficulty")
st.dataframe(schedule, use_container_width=True)
st.line_chart(schedule.set_index("match_date")["schedule_difficulty_index"])