import sqlite3
import os
from datetime import datetime
from accounting import add_transaction

# ==============================
# Paths
# ==============================
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "isp_billing.db")

BILLS_DIR = "bills"
os.makedirs(BILLS_DIR, exist_ok=True)


# --------------------------------------------------
# Create OR update bill (LOCKS PAID bills)
# --------------------------------------------------
def create_or_update_bill(customer_id, amount, due_date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    bill_month = datetime.now().strftime("%Y-%m")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT id, status FROM bills
        WHERE customer_id = ? AND bill_month = ?
    """, (customer_id, bill_month))

    bill = cursor.fetchone()

    if bill:
        bill_id, status = bill

        # 🔒 Do NOT touch PAID bills
        if status == "PAID":
            conn.close()
            return False

        cursor.execute("""
            UPDATE bills
            SET amount = ?, due_date = ?
            WHERE id = ?
        """, (amount, due_date, bill_id))

    else:
        cursor.execute("""
            INSERT INTO bills
            (customer_id, bill_month, amount, due_date, status, created_at)
            VALUES (?, ?, ?, ?, 'UNPAID', ?)
        """, (customer_id, bill_month, amount, due_date, created_at))

    conn.commit()
    conn.close()
    return True


# --------------------------------------------------
# BULK: Generate bills for ALL customers
# --------------------------------------------------
def generate_monthly_bills_for_all(due_date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    bill_month = datetime.now().strftime("%Y-%m")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ Only ACTIVE customers will get bills
    cursor.execute("""
        SELECT id, monthly_amount
        FROM customers
        WHERE status = 'ACTIVE'
    """)
    customers = cursor.fetchall()

    created_count = 0

    for customer_id, amount in customers:
        cursor.execute("""
            SELECT status FROM bills
            WHERE customer_id = ? AND bill_month = ?
        """, (customer_id, bill_month))

        row = cursor.fetchone()

        # Skip PAID bills
        if row and row[0] == "PAID":
            continue

        # Update UNPAID bill
        if row:
            cursor.execute("""
                UPDATE bills
                SET amount = ?, due_date = ?
                WHERE customer_id = ? AND bill_month = ?
            """, (amount, due_date, customer_id, bill_month))
        else:
            cursor.execute("""
                INSERT INTO bills
                (customer_id, bill_month, amount, due_date, status, created_at)
                VALUES (?, ?, ?, ?, 'UNPAID', ?)
            """, (customer_id, bill_month, amount, due_date, created_at))
            created_count += 1

    conn.commit()
    conn.close()
    return created_count


# --------------------------------------------------
# Mark bill as PAID (AUTO ACCOUNTING)
# --------------------------------------------------
def mark_bill_paid(bill_id, payment_method, receipt_no):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT customer_id, amount, status
        FROM bills WHERE id = ?
    """, (bill_id,))
    row = cursor.fetchone()

    if not row or row[2] == "PAID":
        conn.close()
        return False

    customer_id, amount, _ = row

    # Update bill
    cursor.execute("""
        UPDATE bills
        SET status = 'PAID',
            payment_method = ?,
            payment_date = ?,
            receipt_no = ?
        WHERE id = ?
    """, (payment_method, payment_date, receipt_no, bill_id))

    # Get customer name
    cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,))
    result = cursor.fetchone()
    customer_name = result[0] if result else "Unknown"

    # ✅ ADD TRANSACTION BEFORE COMMIT
    cursor.execute("""
        INSERT INTO transactions
        (type, category, amount, note, date,
         bill_id, payment_date, created_at,
         customer, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "INCOME",
        "Bill Payment",
        amount,
        f"Bill #{bill_id} Payment",
        payment_date,
        bill_id,
        payment_date,
        payment_date,
        customer_name,
        payment_method
    ))

    conn.commit()
    conn.close()

    return True

# --------------------------------------------------
# Get all bills
# --------------------------------------------------
def get_bills():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.id,
               c.name,
               b.bill_month,
               b.amount,
               b.due_date,
               b.status,
               IFNULL(b.payment_method, ''),
               IFNULL(b.receipt_no, ''), 
               IFNULL(b.payment_date, ''),
               IFNULL(b.reminder_count, 0),
               IFNULL(b.last_reminder_date, '')
        FROM bills b
        JOIN customers c ON b.customer_id = c.id
        ORDER BY b.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


# --------------------------------------------------
# Get single bill
# --------------------------------------------------
def get_bill_by_id(bill_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, customer_id, bill_month, amount, due_date, status
        FROM bills
        WHERE id = ?
    """, (bill_id,))

    row = cursor.fetchone()
    conn.close()
    return row


# --------------------------------------------------
# Update unpaid bill
# --------------------------------------------------
def update_unpaid_bill(bill_id, amount, due_date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bills
        SET amount = ?, due_date = ?
        WHERE id = ? AND status = 'UNPAID'
    """, (amount, due_date, bill_id))

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated > 0


# --------------------------------------------------
# Reminder tracking
# --------------------------------------------------
def increment_bill_reminder(bill_id, date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bills
        SET 
            reminder_count = COALESCE(reminder_count, 0) + 1,
            last_reminder_date = ?
        WHERE id = ?
    """, (date, bill_id))

    conn.commit()
    conn.close()