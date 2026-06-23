def setup_database(db_path):
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        address TEXT,
        plan_name TEXT,
        monthly_amount REAL,
        status TEXT DEFAULT 'ACTIVE'
    );

    CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    bill_month TEXT,
    amount REAL,
    due_date TEXT,
    status TEXT,
    payment_method TEXT,
    payment_date TEXT,
    created_at TEXT,
    reminder_count INTEGER DEFAULT 0,
    last_reminder_date TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER,
        amount REAL,
        method TEXT,
        status TEXT,
        reference TEXT,
        paid_date TEXT,
        FOREIGN KEY(bill_id) REFERENCES bills(id)
    );

    CREATE TABLE IF NOT EXISTS message_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        message TEXT,
        type TEXT,
        status TEXT,
        sent_at TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );
    """)

    conn.commit()
    conn.close()