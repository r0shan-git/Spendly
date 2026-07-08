"""
Registration feature tests for Spendly.
Covers: success path, hashing, case-insensitive email, all validation
errors (missing fields, invalid email, short password, password mismatch,
name/email length limits, duplicate email), value preservation on error,
and logged-in user redirect.
"""

import database.db as db_module


# -- Helpers ----------------------------------------------------------

VALID_USER = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "securepass123",
    "confirm_password": "securepass123",
}


def register(client, data=None, **overrides):
    """POST /register with VALID_USER merged with any overrides."""
    payload = dict(data or VALID_USER, **overrides)
    return client.post("/register", data=payload, follow_redirects=False)


# -- Tests ------------------------------------------------------------


def test_register_page_loads(client):
    """GET /register returns 200 with the expected heading."""
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create your account" in resp.data


def test_register_success(client):
    """Valid registration redirects to /login with a success flash."""
    resp = register(client)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # Follow the redirect and check for the success message
    resp2 = client.get("/login")
    assert b"Registration successful" in resp2.data


def test_password_is_hashed(client):
    """The stored password_hash is not the plaintext password."""
    register(client)
    conn = db_module.get_db()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE email = ?",
        (VALID_USER["email"],),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["password_hash"] != VALID_USER["password"]
    # Werkzeug hashes start with a method identifier
    assert row["password_hash"].startswith(("scrypt:", "pbkdf2:"))


def test_email_case_insensitive(client):
    """Registering with a different case of an existing email is rejected."""
    register(client, email="user@test.com")
    resp = register(client, email="USER@TEST.COM")

    assert resp.status_code == 200
    assert b"already exists" in resp.data


def test_missing_name(client):
    """Omitting the name field shows an error."""
    resp = register(client, name="")
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data


def test_missing_email(client):
    """Omitting the email field shows an error."""
    resp = register(client, email="")
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data


def test_missing_password(client):
    """Omitting the password field shows an error."""
    resp = register(client, password="")
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data


def test_missing_confirm_password(client):
    """Omitting the confirm_password field shows an error."""
    resp = register(client, confirm_password="")
    assert resp.status_code == 200
    assert b"All fields are required" in resp.data


def test_invalid_email_format(client):
    """A malformed email triggers a format error."""
    resp = register(client, email="notanemail")
    assert resp.status_code == 200
    assert b"valid email" in resp.data


def test_short_password(client):
    """A password shorter than 8 characters is rejected."""
    resp = register(client, password="short", confirm_password="short")
    assert resp.status_code == 200
    assert b"at least 8 characters" in resp.data


def test_password_mismatch(client):
    """Mismatched password and confirm_password triggers an error."""
    resp = register(client, password="securepass123", confirm_password="different1")
    assert resp.status_code == 200
    assert b"Passwords do not match" in resp.data


def test_name_too_long(client):
    """A name exceeding 100 characters is rejected."""
    long_name = "A" * 101
    resp = register(client, name=long_name)
    assert resp.status_code == 200
    assert b"100 characters" in resp.data


def test_email_too_long(client):
    """An email exceeding 255 characters is rejected."""
    long_email = "a" * 247 + "@test.com"  # 256 chars total
    assert len(long_email) > 255
    resp = register(client, email=long_email)
    assert resp.status_code == 200
    assert b"255 characters" in resp.data


def test_duplicate_email(client):
    """Registering the same email twice shows a duplicate error."""
    register(client)
    resp = register(client)
    assert resp.status_code == 200
    assert b"already exists" in resp.data


def test_values_preserved_on_error(client):
    """On validation failure, name and email are preserved in the form."""
    resp = register(client, name="Keep Me", email="keep@me.com", password="short",
                    confirm_password="short")
    assert resp.status_code == 200
    assert b"Keep Me" in resp.data
    assert b"keep@me.com" in resp.data


def test_logged_in_user_redirected(client):
    """A user with an active session is redirected away from /register."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    resp = client.get("/register")
    assert resp.status_code == 302
    assert "/register" not in resp.headers["Location"]
