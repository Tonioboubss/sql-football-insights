"""Shared pytest fixtures for all test modules."""

import sqlite3
from pathlib import Path

import pytest

DB_PATH = Path(__file__).parent.parent / "football.db"


@pytest.fixture
def conn():
    """A fresh connection to the actual project database for each test."""
    connection = sqlite3.connect(DB_PATH)
    yield connection
    connection.close()