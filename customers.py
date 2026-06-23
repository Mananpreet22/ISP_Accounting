import sqlite3
import os

import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "isp_billing.db")


# ==================================================
# 🔍 VALIDATION HELPERS
# ==================================================

def is_valid_phone(phone):
    return phone.isdigit() and len(phone) == 10


def is_valid_email(email):
    if not email:
        return True  # optional field allowed
    return "@" in email and "." in email


# ==================================================
# ➕ ADD CUSTOMER
# ==================================================

def add_customer(name, phone, email, address, plan, amount, status="ACTIVE"):
    if not name:
        raise ValueError("Name is required")

    if not is_valid_phone(phone):
        raise ValueError("Phone number must be exactly 10 digits")

    if not is_valid_email(email):
        raise ValueError("Invalid email format")

    try:
        amount = float(amount)
    except:
        raise ValueError("Amount must be a number")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()


    cur.execute("""
        INSERT INTO customers
        (name, phone, email, address, plan_name, monthly_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, phone, email, address, plan, amount, status))

    conn.commit()
    conn.close()
    return True

def check_duplicate_phone(phone):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT name FROM customers WHERE phone = ?", (phone,))
    result = cur.fetchall()

    conn.close()
    return result  # list of matching customers

# ==================================================
# 📋 GET ALL CUSTOMERS
# ==================================================

def get_all_customers():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            name,
            phone,
            email,
            address,
            plan_name,
            monthly_amount,
            status
        FROM customers
        ORDER BY name
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


# ==================================================
# 🔍 GET CUSTOMER BY ID
# ==================================================

def get_customer_by_id(customer_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            name,
            phone,
            email,
            address,
            plan_name,
            monthly_amount,
            status
        FROM customers
        WHERE id = ?
    """, (customer_id,))

    row = cur.fetchone()
    conn.close()
    return row


# ==================================================
# ✏️ UPDATE CUSTOMER
# ==================================================

def update_customer(customer_id, name, phone, email, address, plan, amount, status):
    if not name:
        raise ValueError("Name is required")

    if not is_valid_phone(phone):
        raise ValueError("Phone number must be exactly 10 digits")

    if not is_valid_email(email):
        raise ValueError("Invalid email format")

    try:
        amount = float(amount)
    except:
        raise ValueError("Amount must be a number")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()


    cur.execute("""
        UPDATE customers
        SET
            name = ?,
            phone = ?,
            email = ?,
            address = ?,
            plan_name = ?,
            monthly_amount = ?,
            status = ?
        WHERE id = ?
    """, (name, phone, email, address, plan, amount, status, customer_id))

    conn.commit()
    conn.close()
    return True


# ==================================================
# ❌ DELETE CUSTOMER (SAFE)
# ==================================================

def delete_customer(customer_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Prevent deletion if bills exist
    cur.execute("""
        SELECT COUNT(*) FROM bills WHERE customer_id = ?
    """, (customer_id,))

    if cur.fetchone()[0] > 0:
        conn.close()
        return False

    cur.execute("""
        DELETE FROM customers WHERE id = ?
    """, (customer_id,))

    conn.commit()
    conn.close()
    return True


# ==================================================
# 📊 CUSTOMER STATUS REPORT
# ==================================================

def get_customer_status_report():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT status, COUNT(*)
        FROM customers
        GROUP BY status
    """)

    data = cur.fetchall()
    conn.close()
    return data