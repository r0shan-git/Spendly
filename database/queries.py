import sqlite3
from database.db import get_db

def get_user_by_id(user_id):
    """
    Fetches user info (name, email, member_since).
    member_since should be formatted as 'Month YYYY'.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        
        created_at = row["created_at"]
        from datetime import datetime
        member_since = "Unknown"
        if created_at:
            try:
                dt = datetime.strptime(str(created_at)[:10], "%Y-%m-%d")
                member_since = dt.strftime("%B %Y")
            except (TypeError, ValueError):
                member_since = created_at
        
        return {
            "name": row["name"],
            "email": row["email"],
            "created_at": row["created_at"],
            "member_since": member_since
        }
    finally:
        conn.close()

def get_summary_stats(user_id):
    """
    Computes total spent, transaction count, and top category.
    Returns a dict: {"total_spent": float, "transaction_count": int, "top_category": str}
    """
    conn = get_db()
    try:
        stats = conn.execute(
            """
            SELECT COUNT(id) AS transaction_count,
                   COALESCE(SUM(amount), 0.0) AS total_spent
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        
        count = stats["transaction_count"]
        total_spent = float(stats["total_spent"])
        
        if count == 0:
            return {
                "total_spent": 0.0,
                "transaction_count": 0,
                "top_category": "—"
            }
        
        top_row = conn.execute(
            """
            SELECT category
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY SUM(amount) DESC, category ASC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        
        top_category = top_row["category"] if top_row else "—"
        
        return {
            "total_spent": total_spent,
            "transaction_count": count,
            "top_category": top_category
        }
    finally:
        conn.close()

def get_paginated_transactions(user_id, limit=10, offset=0):
    """
    Fetches paginated transactions for a user, sorted newest first.
    Returns a list of dicts.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, amount, category, date, description
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()
        
        return [
            {
                "id": row["id"],
                "amount": row["amount"],
                "category": row["category"],
                "date": row["date"],
                "description": row["description"]
            }
            for row in rows
        ]
    finally:
        conn.close()

def get_transaction(transaction_id, user_id):
    """
    Fetches a single transaction matching transaction_id and user_id.
    """
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT id, user_id, amount, category, date, description
        FROM expenses
        WHERE id = ? AND user_id = ?
    """, (transaction_id, user_id)).fetchone()
    conn.close()
    return row

def add_transaction(user_id, amount, category, date, description):
    """
    Inserts a new transaction into the expenses table.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, category, date, description))
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id

def edit_transaction(transaction_id, user_id, amount, category, date, description):
    """
    Updates an existing transaction.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE expenses
        SET amount = ?, category = ?, date = ?, description = ?
        WHERE id = ? AND user_id = ?
    """, (amount, category, date, description, transaction_id, user_id))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount > 0

def delete_transaction(transaction_id, user_id):
    """
    Deletes a transaction.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM expenses
        WHERE id = ? AND user_id = ?
    """, (transaction_id, user_id))
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount > 0

def get_category_breakdown(user_id):
    """
    Computes category-wise breakdown totals and percentages.
    Percentages must sum to exactly 100.
    """
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total_amount DESC
        """, (user_id,)).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    breakdown = []
    total_spending = 0.0
    for row in rows:
        amount = float(row["total_amount"])
        total_spending += amount
        breakdown.append({
            "category": row["category"],
            "total_amount": amount
        })

    if total_spending == 0:
        return []

    sum_percentages = 0
    for item in breakdown:
        pct = round((item["total_amount"] / total_spending) * 100)
        item["percentage"] = pct
        sum_percentages += pct

    remainder = 100 - sum_percentages
    breakdown[0]["percentage"] += remainder

    return breakdown
