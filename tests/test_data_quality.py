"""Tests for our interaction with the football-data.org API.

Note: these tests call the real API. In a larger codebase we would mock
these HTTP calls to keep tests fast and independent of network/rate
limits -- kept live here given the project's scope.
"""

import requests

from src.config import API_TOKEN, BASE_URL, COMPETITIONS, SEASON


def test_token_is_valid_and_competition_codes_exist():
    """Our token must work, and our 3 target competition codes must
    still exist in the API's competition list."""
    response = requests.get(f"{BASE_URL}/competitions", headers={"X-Auth-Token": API_TOKEN})
    assert response.status_code == 200

    available_codes = {c["code"] for c in response.json()["competitions"]}
    for code in COMPETITIONS:
        assert code in available_codes


def test_invalid_token_is_rejected():
    """A bad token must fail clearly, not silently succeed."""
    response = requests.get(
        f"{BASE_URL}/competitions/PL",
        headers={"X-Auth-Token": "invalid_token_on_purpose"},
    )
    assert response.status_code in (400, 401, 403)


def test_target_season_is_fully_completed():
    """The 2025-26 season we've chosen must be entirely played out --
    otherwise our analysis would be built on an incomplete dataset."""
    response = requests.get(
        f"{BASE_URL}/competitions/PL/matches",
        headers={"X-Auth-Token": API_TOKEN},
        params={"season": SEASON},
    )
    assert response.status_code == 200

    result_set = response.json()["resultSet"]
    assert result_set["played"] == result_set["count"]