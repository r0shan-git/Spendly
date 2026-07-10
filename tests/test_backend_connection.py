import pytest
import database.db as db_module
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
from werkzeug.security import generate_password_hash

# Helper to create a user and return their ID
def create_test_user(name="Test User", email="test@example.com"):
    conn = db_module.get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email.lower(), generate_password_hash("password123"), "2026-07-10 12:00:00")
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

# Helper to add expenses
def create_test_expense(user_id, amount, category, date, description):
    conn = db_module.get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description)
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id

@pytest.fixture
def auth_client(client):
    """Helper fixture that logs in a test user and seeds them in the DB."""
    # Seed user in DB
    conn = db_module.get_db()
    conn.execute("INSERT OR IGNORE INTO users (id, name, email, password_hash) VALUES (1, 'Test User', 'test@example.com', 'hash')")
    conn.commit()
    conn.close()

    # Set up session
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"
    
    return client

# ----------------- Query Functions Tests -----------------

def test_get_user_by_id_exists(client):
    user_id = create_test_user("Alice Smith", "alice@example.com")
    user = get_user_by_id(user_id)
    assert user is not None
    assert user["name"] == "Alice Smith"
    assert user["email"] == "alice@example.com"
    assert user["member_since"] == "July 2026"

def test_get_user_by_id_not_found(client):
    user = get_user_by_id(9999)
    assert user is None

def test_get_summary_stats_empty(client):
    user_id = create_test_user()
    stats = get_summary_stats(user_id)
    assert stats == {
        "total_spent": 0.0,
        "transaction_count": 0,
        "top_category": "—"
    }

def test_get_summary_stats_with_data(client):
    user_id = create_test_user()
    create_test_expense(user_id, 150.00, "Food", "2026-07-01", "Lunch")
    create_test_expense(user_id, 300.00, "Bills", "2026-07-02", "Internet")
    create_test_expense(user_id, 250.00, "Food", "2026-07-03", "Dinner")
    
    stats = get_summary_stats(user_id)
    assert stats["total_spent"] == 700.0
    assert stats["transaction_count"] == 3
    assert stats["top_category"] == "Food"

def test_get_paginated_transactions(client):
    user_id = create_test_user()
    create_test_expense(user_id, 100.0, "Food", "2026-07-01", "Exp 1")
    create_test_expense(user_id, 200.0, "Bills", "2026-07-02", "Exp 2")
    create_test_expense(user_id, 300.0, "Shopping", "2026-07-03", "Exp 3")
    
    txs = get_paginated_transactions(user_id, limit=2, offset=0)
    assert len(txs) == 2
    assert txs[0]["amount"] == 300.0
    assert txs[0]["category"] == "Shopping"
    assert txs[1]["amount"] == 200.0
    assert txs[1]["category"] == "Bills"
    
    txs_page2 = get_paginated_transactions(user_id, limit=2, offset=2)
    assert len(txs_page2) == 1
    assert txs_page2[0]["amount"] == 100.0
    assert txs_page2[0]["category"] == "Food"

def test_add_transaction_unit(client):
    user_id = create_test_user()
    tx_id = add_transaction(user_id=user_id, amount=100.50, category="Food", date="2026-07-10", description="Lunch")
    assert tx_id is not None
    assert tx_id > 0

    tx = get_transaction(tx_id, user_id=user_id)
    assert tx is not None
    assert tx["amount"] == 100.50
    assert tx["category"] == "Food"
    assert tx["date"] == "2026-07-10"
    assert tx["description"] == "Lunch"

def test_edit_transaction_unit(client):
    user_id = create_test_user()
    tx_id = add_transaction(user_id=user_id, amount=100.50, category="Food", date="2026-07-10", description="Lunch")
    
    success = edit_transaction(tx_id, user_id=user_id, amount=200.75, category="Bills", date="2026-07-11", description="Dinner")
    assert success is True

    tx = get_transaction(tx_id, user_id=user_id)
    assert tx is not None
    assert tx["amount"] == 200.75
    assert tx["category"] == "Bills"
    assert tx["date"] == "2026-07-11"
    assert tx["description"] == "Dinner"

def test_delete_transaction_unit(client):
    user_id = create_test_user()
    tx_id = add_transaction(user_id=user_id, amount=100.50, category="Food", date="2026-07-10", description="Lunch")
    
    success = delete_transaction(tx_id, user_id=user_id)
    assert success is True

    tx = get_transaction(tx_id, user_id=user_id)
    assert tx is None

def test_get_category_breakdown_empty(client):
    user_id = create_test_user()
    breakdown = get_category_breakdown(user_id)
    assert breakdown == []

def test_get_category_breakdown_rounding(client):
    user_id = create_test_user()
    # Total = 300, Food = 100 (33.33%), Transport = 100 (33.33%), Bills = 100 (33.33%)
    # Rounded values: 33 + 33 + 33 = 99. Remainder (1) should be absorbed by first category.
    create_test_expense(user_id, 100.00, "Food", "2026-07-01", "Lunch")
    create_test_expense(user_id, 100.00, "Transport", "2026-07-02", "Train")
    create_test_expense(user_id, 100.00, "Bills", "2026-07-03", "Internet")
    
    breakdown = get_category_breakdown(user_id)
    assert len(breakdown) == 3
    
    total_pct = sum(item["percentage"] for item in breakdown)
    assert total_pct == 100
    
    # Check that first category absorbed the remainder
    assert breakdown[0]["percentage"] == 34

# ----------------- Route Access Control Tests -----------------

def test_routes_anonymous_redirect(client):
    # GET /profile redirects to login
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # GET /api/expenses redirects to login
    resp = client.get("/api/expenses")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # GET /api/expenses/category-breakdown redirects to login
    resp = client.get("/api/expenses/category-breakdown")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # GET /expenses/add redirects to login
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # POST /expenses/add redirects to login
    resp = client.post("/expenses/add", data={})
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # GET /expenses/1/edit redirects to login
    resp = client.get("/expenses/1/edit")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # POST /expenses/1/edit redirects to login
    resp = client.post("/expenses/1/edit", data={})
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # GET /expenses/1/delete redirects to login
    resp = client.get("/expenses/1/delete")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

# ----------------- Route Integration Tests -----------------

def test_profile_authenticated_empty(client):
    user_id = create_test_user("No Expenses User", "empty@example.com")
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "No Expenses User"
        
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"No Expenses User" in resp.data
    assert b"empty@example.com" in resp.data
    assert b"Member since July 2026" in resp.data
    assert b"No expenses logged yet" in resp.data

def test_profile_authenticated_with_data(client):
    user_id = create_test_user("John Doe", "john@example.com")
    create_test_expense(user_id, 450.50, "Food", "2026-07-02", "Lunch with colleagues")
    
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = "John Doe"
        
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"John Doe" in resp.data
    assert b"john@example.com" in resp.data
    assert b"Food" in resp.data
    assert b"Lunch with colleagues" in resp.data
    assert b"450.50" in resp.data

def test_api_expenses_pagination(client):
    user_id = create_test_user()
    for i in range(15):
        create_test_expense(user_id, 10.0 + i, "Food", f"2026-07-{i+1:02d}", f"Expense {i}")
        
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        
    # Page 1
    resp = client.get("/api/expenses?page=1&limit=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["expenses"]) == 10
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["total_count"] == 15
    assert data["pagination"]["total_pages"] == 2
    
    # Page 2
    resp = client.get("/api/expenses?page=2&limit=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["expenses"]) == 5
    assert data["pagination"]["current_page"] == 2
    
    # Page 3 (out of bounds)
    resp = client.get("/api/expenses?page=3&limit=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["expenses"]) == 0
    assert data["pagination"]["current_page"] == 3

def test_api_expenses_boundary_values(client):
    user_id = create_test_user()
    create_test_expense(user_id, 100.0, "Food", "2026-07-01", "Lunch")
    
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        
    # Invalid page/limit strings fallback
    resp = client.get("/api/expenses?page=invalid&limit=invalid")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["limit"] == 10
    
    # Negative values fallback
    resp = client.get("/api/expenses?page=-5&limit=-2")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["limit"] == 10

def test_add_expense_route_form_success(auth_client):
    resp = auth_client.post("/expenses/add", data={
        "amount": "150.00",
        "category": "Transport",
        "date": "2026-07-10",
        "description": "Metro card"
    })
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]

    resp2 = auth_client.get("/profile")
    assert b"Expense added successfully" in resp2.data

def test_add_expense_route_json_success(auth_client):
    resp = auth_client.post("/expenses/add", json={
        "amount": 250.75,
        "category": "Shopping",
        "date": "2026-07-10",
        "description": "Shoes"
    })
    assert resp.status_code == 201
    json_data = resp.get_json()
    assert json_data["message"] == "Expense added successfully."
    assert "₹250.75" in json_data["expense"]["amount"]

def test_edit_expense_route_form_success(auth_client):
    tx_id = add_transaction(user_id=1, amount=100.00, category="Food", date="2026-07-10", description="Snack")
    
    resp = auth_client.post(f"/expenses/{tx_id}/edit", data={
        "amount": "120.00",
        "category": "Food",
        "date": "2026-07-11",
        "description": "Snack and drink"
    })
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]

    tx = get_transaction(tx_id, user_id=1)
    assert tx["amount"] == 120.00
    assert tx["date"] == "2026-07-11"

def test_edit_expense_route_json_success(auth_client):
    tx_id = add_transaction(user_id=1, amount=100.00, category="Food", date="2026-07-10", description="Snack")
    
    resp = auth_client.post(f"/expenses/{tx_id}/edit", json={
        "amount": 130.50,
        "category": "Entertainment",
        "date": "2026-07-12",
        "description": "Movie"
    })
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["message"] == "Expense updated successfully."
    assert "₹130.50" in json_data["expense"]["amount"]

def test_delete_expense_route_form_success(auth_client):
    tx_id = add_transaction(user_id=1, amount=100.00, category="Food", date="2026-07-10", description="Snack")
    
    resp = auth_client.post(f"/expenses/{tx_id}/delete")
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]

    assert get_transaction(tx_id, user_id=1) is None

def test_delete_expense_route_json_success(auth_client):
    tx_id = add_transaction(user_id=1, amount=100.00, category="Food", date="2026-07-10", description="Snack")
    
    resp = auth_client.post(f"/expenses/{tx_id}/delete", json={})
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["message"] == "Expense deleted successfully."

def test_add_expense_validation_failures(auth_client):
    # Negative amount
    resp = auth_client.post("/expenses/add", data={
        "amount": "-50.00",
        "category": "Food",
        "date": "2026-07-10",
        "description": "Error"
    })
    assert resp.status_code == 200
    assert b"Amount must be a positive number." in resp.data

    # Invalid category
    resp = auth_client.post("/expenses/add", data={
        "amount": "50.00",
        "category": "InvalidCat",
        "date": "2026-07-10",
        "description": "Error"
    })
    assert resp.status_code == 200
    assert b"Category must be one of" in resp.data

    # Missing date
    resp = auth_client.post("/expenses/add", data={
        "amount": "50.00",
        "category": "Food",
        "date": "",
        "description": "Error"
    })
    assert resp.status_code == 200
    assert b"Date must be present" in resp.data

def test_add_expense_validation_failures_json(auth_client):
    # Negative amount JSON
    resp = auth_client.post("/expenses/add", json={
        "amount": -10.00,
        "category": "Food",
        "date": "2026-07-10",
        "description": "Error"
    })
    assert resp.status_code == 400
    assert b"Amount must be a positive number." in resp.data

    # Invalid category JSON
    resp = auth_client.post("/expenses/add", json={
        "amount": 10.00,
        "category": "InvalidCat",
        "date": "2026-07-10",
        "description": "Error"
    })
    assert resp.status_code == 400
    assert b"Category must be one of" in resp.data

def test_api_category_breakdown_route(auth_client):
    create_test_expense(user_id=1, amount=150.00, category="Food", date="2026-07-01", description="Lunch")
    create_test_expense(user_id=1, amount=300.00, category="Bills", date="2026-07-02", description="Internet")
    
    resp = auth_client.get("/api/expenses/category-breakdown")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["breakdown"]) == 2
    assert data["breakdown"][0]["category"] == "Bills"
    assert data["breakdown"][0]["percentage"] == 67
    assert data["breakdown"][1]["category"] == "Food"
    assert data["breakdown"][1]["percentage"] == 33
