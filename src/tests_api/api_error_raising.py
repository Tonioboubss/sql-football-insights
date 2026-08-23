"""Test script 3: deliberately triggering an error to see the failure mode
and how to handle it with try/except."""

import requests
from config import BASE_URL

response = requests.get(
    f"{BASE_URL}/competitions/PL",
    headers={"X-Auth-Token": "invalid_token_on_purpose"},
)

print("Status code:", response.status_code)
print("Body:", response.json())  # the API usually explains the error here

try:
    response.raise_for_status()
except requests.exceptions.HTTPError as error:
    print(f"Request failed as expected: {error}")