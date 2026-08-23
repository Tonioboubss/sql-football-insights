"""Test script 1: the raw mechanics of an HTTP request, before parsing anything."""

import requests
from config import API_TOKEN, BASE_URL

response = requests.get(
    f"{BASE_URL}/competitions/PL",
    headers={"X-Auth-Token": API_TOKEN},
)

print("Status code:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Raw body (first 300 chars):", response.text[:300])