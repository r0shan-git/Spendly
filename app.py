import functools
import os
import re
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database and seed demo data on startup
with app.app_context():
    init_db()
    seed_db()



# ------------------------------------------------------------------ #
# Auth decorator                                                      #
# ------------------------------------------------------------------ #

def login_required(f):
    """Decorator that redirects unauthenticated users to the login page."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Redirect logged-in users away from the registration page
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    # --- POST: validate and create account ---
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # 1. All fields required
    if not name or not email or not password or not confirm_password:
        flash("All fields are required.", "error")
        return render_template("register.html", name=name, email=email)

    # 2. Name length
    if len(name) > 100:
        flash("Name must be 100 characters or fewer.", "error")
        return render_template("register.html", name=name, email=email)

    # 3. Email length
    if len(email) > 255:
        flash("Email must be 255 characters or fewer.", "error")
        return render_template("register.html", name=name, email=email)

    # 4. Email format
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please enter a valid email address.", "error")
        return render_template("register.html", name=name, email=email)

    # 5. Password length
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return render_template("register.html", name=name, email=email)

    # 6. Passwords match
    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("register.html", name=name, email=email)

    # 7. Check duplicate email
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)
    ).fetchone()
    if existing:
        conn.close()
        flash("An account with this email already exists.", "error")
        return render_template("register.html", name=name, email=email)

    # --- Insert new user ---
    password_hash = generate_password_hash(password)
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email.lower(), password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Race condition: another request inserted the same email between
        # our SELECT check and this INSERT
        conn.close()
        flash("An account with this email already exists.", "error")
        return render_template("register.html", name=name, email=email)
    finally:
        conn.close()

    flash("Registration successful! Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    # Redirect already-authenticated users away from the login page
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    # --- POST: validate credentials and create session ---
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    # 1. Both fields required
    if not email or not password:
        flash("All fields are required.", "error")
        return render_template("login.html", email=email)

    # 2. Look up user by email
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE LOWER(email) = ?",
            (email.lower(),),
        ).fetchone()

        # 3. Generic error for unknown email or wrong password (prevents enumeration)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html", email=email)
    finally:
        conn.close()

    # 4. Credentials valid — create session
    session.clear()  # Prevent session fixation
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    flash(f"Welcome back, {user['name']}!", "success")
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")




# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
