"""Sanity check: verify the API token works and list all available
competition codes, so we can confirm the exact codes for our 3 target
competitions before hardcoding anything."""

import requests
from config import API_TOKEN, BASE_URL

response = requests.get(
    f"{BASE_URL}/competitions",
    headers={"X-Auth-Token": API_TOKEN},
)
response.raise_for_status()

for competition in response.json()["competitions"]:
    print(competition["code"], "-", competition["name"])