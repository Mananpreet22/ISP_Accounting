import sqlite3


def apply_migrations(db_name):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    # ===============================
    # TRANSACTIONS TABLE (Income)
    # ===============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        category TEXT,
        amount REAL,
        note TEXT,
        date TEXT,
        bill_id INTEGER,
        payment_date TEXT,
        created_at TEXT,
        customer TEXT,
        payment_method TEXT
    )
""")
    # Safely upgrade old versions
    safe_columns = [
        ("bill_id", "INTEGER"),
        ("customer", "TEXT"),
        ("payment_method", "TEXT"),
        ("payment_date", "TEXT"),
        ("created_at", "TEXT")
    ]

    for column, col_type in safe_columns:
        try:
            cur.execute(f"ALTER TABLE transactions ADD COLUMN {column} {col_type}")
        except:
            pass


    # ===============================
    # EXPENSES TABLE
    # ===============================
    cur.execute("""
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


    # ===============================
    # BILLS TABLE UPGRADES
    # ===============================
    try:
        cur.execute("ALTER TABLE bills ADD COLUMN tax REAL DEFAULT 0")
    except:
        pass

    try:
        cur.execute("ALTER TABLE bills ADD COLUMN discount REAL DEFAULT 0")
    except:
        pass


   # ===============================
# 🔥 ADD REMINDER SYSTEM (FIX)
# ===============================
    cur.execute("PRAGMA table_info(bills)")
    columns = [col[1] for col in cur.fetchall()]

    if "reminder_count" not in columns:
        cur.execute("ALTER TABLE bills ADD COLUMN reminder_count INTEGER DEFAULT 0")

    if "last_reminder_date" not in columns:
        cur.execute("ALTER TABLE bills ADD COLUMN last_reminder_date TEXT")

    # ===============================
    # CUSTOMERS TABLE STATUS COLUMN
    # ===============================
    cur.execute("PRAGMA table_info(customers)")
    columns = [col[1] for col in cur.fetchall()]

    if "status" not in columns:
        cur.execute("ALTER TABLE customers ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
        print("✅ Added status column to customers")


# ===============================
# 🔥 ADD RECEIPT NUMBER
# ===============================
    cur.execute("PRAGMA table_info(bills)")
    columns = [col[1] for col in cur.fetchall()]

    if "receipt_no" not in columns:
        cur.execute("ALTER TABLE bills ADD COLUMN receipt_no TEXT")


    conn.commit()
    conn.close()