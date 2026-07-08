"""
Shared pytest fixtures for the Spendly test suite.
Creates an isolated temporary database for each test function.
"""

import os
import tempfile

import pytest

# Patch DB_PATH before importing app so all database operations
# target the temporary file instead of the real database.
import database.db as db_module
from database.db import init_db


@pytest.fixture()
def client():
    """
    Yields a Flask test client backed by a fresh temporary database.
    The database is created, schema is initialised (but NOT seeded),
    and torn down after each test.
    """
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Patch the module-level DB_PATH so get_db() uses our temp file
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = db_path

    # Import app after patching so the startup init_db/seed_db
    # runs against the temp database
    from app import app

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    # Initialise schema in the temp database
    with app.app_context():
        init_db()

    with app.test_client() as test_client:
        with app.app_context():
            yield test_client

    # Teardown: restore original path and remove temp file
    db_module.DB_PATH = original_db_path
    os.close(db_fd)
    os.unlink(db_path)
