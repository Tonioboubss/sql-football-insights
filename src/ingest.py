"""Fetch and cache raw API responses for our 3 target competitions.

This script only calls the API and stores the raw JSON responses under
data/raw/ -- it does not transform or load anything into the database.
"""

import json
import logging
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import API_TOKEN, BASE_URL, COMPETITIONS, SEASON

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
REQUEST_DELAY_SECONDS = 7  # stay safely under the free tier's 10 requests/minute limit
HEADERS = {"X-Auth-Token": API_TOKEN}


def build_session() -> requests.Session:
    """Build a session that automatically retries transient failures --
    connection drops, server errors (5xx), and rate limiting (429) --
    with an increasing delay between attempts, instead of crashing the
    whole ingestion run."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,  # waits 2s, then 4s, then 8s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    return session


def fetch_and_cache(
    session: requests.Session,
    url: str,
    output_path: Path,
    params: dict | None = None,
    force_refresh: bool = False,
) -> bool:
    """Call the API and save the raw JSON response to disk, unless a
    cached copy already exists. Returns True if an actual network call
    was made, False if a cached file was reused -- the caller uses this
    to skip the rate-limit delay when nothing was actually fetched."""
    if output_path.exists() and not force_refresh:
        logger.info("Skipping %s -- already cached at %s", url, output_path)
        return False

    logger.info("Fetching %s (params=%s)", url, params)
    response = session.get(url, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    output_path.write_text(json.dumps(response.json(), indent=2))
    logger.info("Saved to %s", output_path)
    return True


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = build_session()

    for code in COMPETITIONS:
        if fetch_and_cache(session, f"{BASE_URL}/competitions/{code}", RAW_DIR / f"{code}_competition.json"):
            time.sleep(REQUEST_DELAY_SECONDS)

        if fetch_and_cache(
            session,
            f"{BASE_URL}/competitions/{code}/teams",
            RAW_DIR / f"{code}_teams.json",
            params={"season": SEASON},
        ):
            time.sleep(REQUEST_DELAY_SECONDS)

        if fetch_and_cache(
            session,
            f"{BASE_URL}/competitions/{code}/matches",
            RAW_DIR / f"{code}_matches.json",
            params={"season": SEASON},
        ):
            time.sleep(REQUEST_DELAY_SECONDS)


if __name__ == "__main__":
    main()