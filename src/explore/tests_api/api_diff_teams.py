"""Diagnostic: check whether the teams roster actually differs between
the current season and the 2025-26 season we're now targeting."""

import requests
from config import API_TOKEN, BASE_URL

current = requests.get(
    f"{BASE_URL}/competitions/PL/teams",
    headers={"X-Auth-Token": API_TOKEN},
).json()

past_season = requests.get(
    f"{BASE_URL}/competitions/PL/teams",
    headers={"X-Auth-Token": API_TOKEN},
    params={"season": 2025},
).json()

current_names = {team["name"] for team in current["teams"]}
past_names = {team["name"] for team in past_season["teams"]}

print("Only in current (2026-27) roster:", current_names - past_names)
print("Only in 2025-26 roster:", past_names - current_names)