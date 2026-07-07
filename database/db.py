import os
import sqlite3
from werkzeug.security import generate_password_hash

# Path to the database file at the project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")

def get_db():
    """
    Opens a connection to the SQLite database.
    Configures dictionary-like row factory and enables foreign key constraints.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """
    Initializes the database schema by creating users and expenses tables
    if they do not already exist.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    
    # Create expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)
    
    conn.commit()
    conn.close()

def seed_db():
    """
    Seeds development demo data into the database if the users table is empty.
    Creates a demo user and inserts 8 sample expenses.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if database has already been seeded (to prevent duplication)
    cursor.execute("SELECT 1 FROM users LIMIT 1;")
    if cursor.fetchone() is not None:
        conn.close()
        return
        
    # Insert Demo User
    demo_name = "Demo User"
    demo_email = "demo@spendly.com"
    demo_password_hash = generate_password_hash("demo123")
    
    cursor.execute("""
        INSERT INTO users (name, email, password_hash)
        VALUES (?, ?, ?);
    """, (demo_name, demo_email, demo_password_hash))
    
    demo_user_id = cursor.lastrowid
    
    # 8 sample expenses covering all fixed categories
    # Dates spread across July 2026 (current month in user local time context)
    sample_expenses = [
        (demo_user_id, 450.50, "Food", "2026-07-02", "Lunch with colleagues"),
        (demo_user_id, 1200.00, "Bills", "2026-07-05", "Internet broadband monthly bill"),
        (demo_user_id, 150.00, "Transport", "2026-07-08", "Metro smart card recharge"),
        (demo_user_id, 850.00, "Health", "2026-07-10", "Multivitamins and prescription medicine"),
        (demo_user_id, 500.00, "Entertainment", "2026-07-12", "Movie tickets"),
        (demo_user_id, 2499.00, "Shopping", "2026-07-15", "New running shoes"),
        (demo_user_id, 350.00, "Other", "2026-07-18", "Home cleaning supplies"),
        (demo_user_id, 650.00, "Food", "2026-07-20", "Grocery shopping"),
    ]
    
    cursor.executemany("""
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?);
    """, sample_expenses)
    
    conn.commit()
    conn.close()
