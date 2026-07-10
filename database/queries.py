import sqlite3
from database.db import get_db

def get_user_by_id(user_id):
    """
    Fetches user info (name, email, member_since).
    member_since should be formatted as 'Month YYYY'.
    """
    pass

def get_summary_stats(user_id):
    """
    Computes total spent, transaction count, and top category.
    Returns a dict: {"total_spent": float, "transaction_count": int, "top_category": str}
    """
    pass

def get_paginated_transactions(user_id, limit=10, offset=0):
    """
    Fetches paginated transactions for a user, sorted newest first.
    Returns a list of dicts.
    """
    pass

def add_transaction(user_id, amount, category, date, description):
    """
    Inserts a new transaction into the expenses table.
    """
    pass

def edit_transaction(transaction_id, user_id, amount, category, date, description):
    """
    Updates an existing transaction.
    """
    pass

def delete_transaction(transaction_id, user_id):
    """
    Deletes a transaction.
    """
    pass

def get_category_breakdown(user_id):
    """
    Computes category-wise breakdown totals and percentages.
    Percentages must sum to exactly 100.
    """
    pass
