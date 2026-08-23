"""Test script 2: parsing the JSON body into Python objects and navigating it."""

import requests
from config import API_TOKEN, BASE_URL

response = requests.get(
    f"{BASE_URL}/competitions/PL/teams",
    headers={"X-Auth-Token": API_TOKEN},
)
response.raise_for_status()  # raises an exception if the status code is not 2xx

data = response.json()       # turns the JSON body into a Python dict
print("Top-level keys:", data.keys())

teams = data["teams"]        # the actual list of teams is nested under this key
print(f"Number of teams: {len(teams)}")
print("First team:", teams[0]["name"], "- id:", teams[0]["id"])