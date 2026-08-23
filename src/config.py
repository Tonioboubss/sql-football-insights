"""Centralized configuration for the football-sql-pipeline project.

Loads secrets from environment variables via a local .env file, so no
credential is ever hardcoded or committed to version control.
"""

import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ["FOOTBALL_DATA_API_TOKEN"]
BASE_URL = "https://api.football-data.org/v4"

# Confirmed via a call to the /v4/competitions endpoint
COMPETITIONS = {
    "PL": "Premier League",
    "FL1": "Ligue 1",
    "CL": "UEFA Champions League",
}

# We deliberately target the 2025-26 season (already completed) rather
# than the current 2026-27 season, which had barely started when this
# project began -- not enough matches yet for a meaningful analysis,
# and the Champions League hadn't even kicked off.
SEASON = 2025