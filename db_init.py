import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "isp_billing.db")


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # =========================
    # CUSTOMERS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            address TEXT,
            plan TEXT,
            status TEXT
        )
    """)

    # =========================
    # TRANSACTIONS TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            category TEXT,
            amount REAL,
            note TEXT,
            date TEXT,
            bill_id INTEGER,
            payment_date TEXT,
            receipt_no TEXT,
            created_at TEXT,
            customer TEXT,
            payment_method TEXT
        )
    """)

    # =========================
    # EXPENSES TABLE
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            description TEXT,
            amount REAL,
            payment_method TEXT,
            expense_date TEXT,
            created_at TEXT
        )
    """)

    # =========================
    # 🔥 UPDATED BILLS TABLE (FULL VERSION)
    # =========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            bill_month TEXT,
            amount REAL,
            status TEXT,
            due_date TEXT,
            payment_method TEXT,
            payment_date TEXT,
            reminder_count INTEGER DEFAULT 0,
            last_reminder_date TEXT,
            created_at TEXT
        )
    """)

    # =========================
    # 🔥 SAFE MIGRATION SYSTEM
    # =========================
    columns_to_add = [
        ("bill_month", "TEXT"),
        ("payment_method", "TEXT"),
        ("payment_date", "TEXT"),
        ("last_reminder_date", "TEXT"),
        ("created_at", "TEXT")
    ]

    for col, col_type in columns_to_add:
        if not column_exists(cursor, "bills", col):
            cursor.execute(f"ALTER TABLE bills ADD COLUMN {col} {col_type}")

    # Ensure reminder_count exists (extra safety)
    if not column_exists(cursor, "bills", "reminder_count"):
        cursor.execute(
            "ALTER TABLE bills ADD COLUMN reminder_count INTEGER DEFAULT 0"
        )
    if not column_exists(cursor, "transactions", "receipt_no"):
        cursor.execute(
        "ALTER TABLE transactions ADD COLUMN receipt_no TEXT"
    )

    conn.commit()
    conn.close()