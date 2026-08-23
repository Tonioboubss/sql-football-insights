"""Test script: save a single API response as a JSON file on disk."""

import json
from pathlib import Path

import requests
from config import API_TOKEN, BASE_URL

response = requests.get(
    f"{BASE_URL}/competitions/PL/teams",
    headers={"X-Auth-Token": API_TOKEN},
)
response.raise_for_status()
data = response.json()

output_dir = Path(__file__).parent.parent / "data" / "raw"
output_dir.mkdir(parents=True, exist_ok=True)  # create the folder if it doesn't exist yet

output_path = output_dir / "PL_teams.json"
output_path.write_text(json.dumps(data, indent=2))

print(f"Saved {len(data['teams'])} teams to {output_path}")