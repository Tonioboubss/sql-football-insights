"""Diagnostic: check whether the free tier actually allows querying an
already-completed past season via the `season` parameter, or whether
it's truly hard-restricted to the current season only."""

import requests
from config import API_TOKEN, BASE_URL

response = requests.get(
    f"{BASE_URL}/competitions/PL/matches",
    headers={"X-Auth-Token": API_TOKEN},
    params={"season": 2025},  # the 2025-26 season, already completed
)

print("Status code:", response.status_code)
print("Body (first 500 chars):", response.text[:500])