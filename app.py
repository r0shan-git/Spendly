import functools
import os
import re
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_paginated_transactions,
    get_transaction,
    add_transaction,
    edit_transaction,
    delete_transaction,
    get_category_breakdown
)

app = Flask(__name__)
app.secret_key = os.urandom(24)


# ------------------------------------------------------------------ #
# Jinja2 custom filters                                               #
# ------------------------------------------------------------------ #

@app.template_filter("inr")
def inr_format(value):
    """
    Format a numeric value using Indian digit grouping and 2 decimal places.
    Example: 123456.5 → "1,23,456.50"
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0.00"

    # Split integer and decimal parts
    integer_part = int(value)
    decimal_part = round((value - integer_part) * 100)
    decimal_str = f"{decimal_part:02d}"

    s = str(integer_part)
    if len(s) <= 3:
        return f"{s}.{decimal_str}"

    # Last 3 digits, then groups of 2 from the right
    result = s[-3:]
    s = s[:-3]
    while s:
        result = s[-2:] + "," + result
        s = s[:-2]

    return f"{result}.{decimal_str}"


@app.template_filter("format_date")
def format_date(value):
    """
    Convert a SQLite datetime string to a human-readable 'Month YYYY' format.
    Example: "2026-07-09 12:34:56" → "July 2026"
    Falls back gracefully if the value is missing or malformed.
    """
    from datetime import datetime
    try:
        dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return dt.strftime("%B %Y")
    except (TypeError, ValueError):
        return value or "Unknown"

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
@login_required
def profile():
    user_id = session["user_id"]
    
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        flash("Your session has expired. Please sign in again.", "error")
        return redirect(url_for("login"))
        
    stats = get_summary_stats(user_id)
    recent_transactions = get_paginated_transactions(user_id, limit=10, offset=0)
    category_breakdown = get_category_breakdown(user_id)

    # Compute initials server-side
    words = [w for w in user["name"].split() if w]
    if not words:
        initials = "?"
    elif len(words) == 1:
        initials = words[0][0].upper()
    else:
        initials = (words[0][0] + words[-1][0]).upper()

    return render_template(
        "profile.html",
        name=user["name"],
        email=user["email"],
        created_at=user["created_at"],
        member_since=user["member_since"],
        expense_count=stats["transaction_count"],
        total_spent=stats["total_spent"],
        top_category=stats["top_category"],
        recent_transactions=recent_transactions,
        category_breakdown=category_breakdown,
        initials=initials,
    )


@app.route("/api/expenses")
@login_required
def api_expenses():
    user_id = session["user_id"]
    
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
        
    try:
        limit = int(request.args.get("limit", 10))
        if limit < 1:
            limit = 10
    except ValueError:
        limit = 10
        
    offset = (page - 1) * limit
    
    stats = get_summary_stats(user_id)
    total_count = stats["transaction_count"]
    
    expenses = get_paginated_transactions(user_id, limit=limit, offset=offset)
    
    import math
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
    
    return {
        "success": True,
        "expenses": expenses,
        "pagination": {
            "current_page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages
        }
    }


@app.route("/api/expenses/category-breakdown")
@login_required
def api_category_breakdown():
    user_id = session["user_id"]
    breakdown_list = get_category_breakdown(user_id)
    return {"success": True, "breakdown": breakdown_list}


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    user_id = session["user_id"]
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json() or {}
            amount_val = data.get("amount")
            category = data.get("category")
            date_val = data.get("date")
            description = data.get("description", "")
        else:
            amount_val = request.form.get("amount")
            category = request.form.get("category")
            date_val = request.form.get("date")
            description = request.form.get("description", "")

        try:
            amount = float(amount_val)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            error_msg = "Amount must be a positive number."
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("add_expense.html", amount=amount_val, category=category, date=date_val, description=description)

        valid_categories = {"Food", "Bills", "Transport", "Health", "Entertainment", "Shopping", "Other"}
        if category not in valid_categories:
            error_msg = f"Category must be one of: {', '.join(sorted(valid_categories))}."
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("add_expense.html", amount=amount_val, category=category, date=date_val, description=description)

        if not date_val or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_val):
            error_msg = "Date must be present and in YYYY-MM-DD format."
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("add_expense.html", amount=amount_val, category=category, date=date_val, description=description)

        transaction_id = add_transaction(user_id, amount, category, date_val, description)

        if request.is_json:
            return jsonify({
                "message": "Expense added successfully.",
                "expense": {
                    "id": transaction_id,
                    "amount": f"₹{amount:.2f}",
                    "category": category,
                    "date": date_val,
                    "description": description
                }
            }), 201
        
        flash("Expense added successfully.", "success")
        return redirect(url_for("profile"))

    # GET request
    if request.is_json:
        return jsonify({"categories": ["Food", "Bills", "Transport", "Health", "Entertainment", "Shopping", "Other"]})

    from datetime import date as dt
    today = dt.today().strftime("%Y-%m-%d")
    return render_template("add_expense.html", date=today)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    user_id = session["user_id"]
    
    transaction = get_transaction(id, user_id)
    if not transaction:
        error_msg = "Expense not found."
        if request.is_json:
            return jsonify({"error": error_msg}), 404
        flash(error_msg, "error")
        return redirect(url_for("profile"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json() or {}
            amount_val = data.get("amount")
            category = data.get("category")
            date_val = data.get("date")
            description = data.get("description", "")
        else:
            amount_val = request.form.get("amount")
            category = request.form.get("category")
            date_val = request.form.get("date")
            description = request.form.get("description", "")

        try:
            amount = float(amount_val)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            error_msg = "Amount must be a positive number."
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("edit_expense.html", id=id, amount=amount_val, category=category, date=date_val, description=description)

        valid_categories = {"Food", "Bills", "Transport", "Health", "Entertainment", "Shopping", "Other"}
        if category not in valid_categories:
            error_msg = f"Category must be one of: {', '.join(sorted(valid_categories))}."
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("edit_expense.html", id=id, amount=amount_val, category=category, date=date_val, description=description)

        if not date_val or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_val):
            error_msg = "Date must be present and in YYYY-MM-DD format."
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("edit_expense.html", id=id, amount=amount_val, category=category, date=date_val, description=description)

        edit_transaction(id, user_id, amount, category, date_val, description)

        if request.is_json:
            return jsonify({
                "message": "Expense updated successfully.",
                "expense": {
                    "id": id,
                    "amount": f"₹{amount:.2f}",
                    "category": category,
                    "date": date_val,
                    "description": description
                }
            })
        
        flash("Expense updated successfully.", "success")
        return redirect(url_for("profile"))

    # GET request
    if request.is_json:
        return jsonify({
            "id": transaction["id"],
            "amount": f"₹{transaction['amount']:.2f}",
            "category": transaction["category"],
            "date": transaction["date"],
            "description": transaction["description"]
        })

    return render_template(
        "edit_expense.html",
        id=transaction["id"],
        amount=transaction["amount"],
        category=transaction["category"],
        date=transaction["date"],
        description=transaction["description"]
    )


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete_expense(id):
    user_id = session["user_id"]
    
    transaction = get_transaction(id, user_id)
    if not transaction:
        error_msg = "Expense not found."
        if request.is_json:
            return jsonify({"error": error_msg}), 404
        flash(error_msg, "error")
        return redirect(url_for("profile"))
    
    success = delete_transaction(id, user_id)
    if not success:
        error_msg = "Could not delete expense."
        if request.is_json:
            return jsonify({"error": error_msg}), 400
        flash(error_msg, "error")
        return redirect(url_for("profile"))

    if request.is_json:
        return jsonify({"message": "Expense deleted successfully."})
    
    flash("Expense deleted successfully.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
