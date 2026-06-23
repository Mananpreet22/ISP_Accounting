import sqlite3
from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ==============================
# DATABASE
# ==============================
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "isp_billing.db")


def get_connection():
    return sqlite3.connect(DB_NAME)


# ==============================
# AUTO INCOME (when bill paid)
# ==============================
def add_transaction(bill_id, customer, amount, payment_method):
    conn = get_connection()
    cursor = conn.cursor()

    payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        customer,
        payment_method
    ))

    conn.commit()
    conn.close()


# ==============================
# ADD EXPENSE
# ==============================
def add_expense(category, description, amount, payment_method, date=None):
    conn = get_connection()
    cursor = conn.cursor()

    # 🔥 If no date given → today
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO expenses
        (category, description, amount, payment_method, expense_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        category,
        description,
        amount,
        payment_method,
        date,
        created_at
    ))

    conn.commit()
    conn.close()


# ==============================
# TODAY PROFIT
# ==============================
def get_today_profit():
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # ==========================
    # INCOME
    # ==========================
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM transactions
        WHERE DATE(payment_date) = ?
    """, (today,))
    income = cursor.fetchone()[0] or 0

    # ==========================
    # EXPENSE
    # ==========================
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE DATE(expense_date) = ?
    """, (today,))
    expense = cursor.fetchone()[0] or 0

    conn.close()

    profit = income - expense
    return income, expense, profit


# ==============================
# MONTHLY PROFIT (future reports)
# ==============================
def get_monthly_profit_n1(month=None):
    conn = get_connection()
    cursor = conn.cursor()

    if not month:
        month = datetime.now().strftime("%Y-%m")

    # Income
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM transactions
        WHERE strftime('%Y-%m', payment_date) = ?
    """, (month,))
    income = cursor.fetchone()[0] or 0

    # Expense
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE strftime('%Y-%m', expense_date) = ?
    """, (month,))
    expense = cursor.fetchone()[0] or 0

    conn.close()

    profit = income - expense
    return income, expense, profit


# ==============================
# CATEGORY EXPENSE REPORT
# ==============================
def get_expense_by_category():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, IFNULL(SUM(amount), 0)
        FROM expenses
        GROUP BY category
    """)

    data = cursor.fetchall()
    conn.close()
    return data

# ==============================
# GET ALL EXPENSES
# ==============================
def get_all_expenses():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            category,
            description,
            amount,
            payment_method,
            expense_date
        FROM expenses
        ORDER BY expense_date DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data

# monthly data 

def get_monthly_profit():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # =====================
    # INCOME
    # =====================
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', payment_date) as month,
            IFNULL(SUM(amount), 0)
        FROM transactions
        WHERE payment_date IS NOT NULL
        GROUP BY month
    """)
    income_data = cursor.fetchall()

    # =====================
    # EXPENSE
    # =====================
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', expense_date) as month,
            IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE expense_date IS NOT NULL
        GROUP BY month
    """)
    expense_data = cursor.fetchall()

    conn.close()

    # Convert to dictionary and remove None
    income_dict = {m: v for m, v in income_data if m}
    expense_dict = {m: v for m, v in expense_data if m}

    # 🔥 Remove None months before sorting
    all_months = set(income_dict) | set(expense_dict)
    months = sorted(m for m in all_months if m)

    result = []
    for m in months:
        income = income_dict.get(m, 0)
        expense = expense_dict.get(m, 0)
        profit = income - expense
        result.append((m, income, expense, profit))

    return result


#### Catogory summry function 
def get_expense_category_report():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        GROUP BY category
    """)

    data = cursor.fetchall()
    conn.close()
    return data

# ==============================
# MONTHLY SUMMARY (CURRENT MONTH)
# ==============================
def get_current_month_summary():
    conn = get_connection()
    cursor = conn.cursor()

    month = datetime.now().strftime("%Y-%m")

    # Income
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM transactions
        WHERE strftime('%Y-%m', payment_date) = ?
    """, (month,))
    income = cursor.fetchone()[0] or 0

    # Expense
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE strftime('%Y-%m', expense_date) = ?
    """, (month,))
    expense = cursor.fetchone()[0] or 0

    conn.close()

    profit = income - expense
    return income, expense, profit

# edit expense 

def update_expense(expense_id, category, description, amount, payment_method, expense_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE expenses
        SET category=?,
            description=?,
            amount=?,
            payment_method=?,
            expense_date=?
        WHERE id=?
    """, (category, description, amount, payment_method, expense_date, expense_id))

    conn.commit()
    conn.close()

# delete expense button 
def delete_expense(expense_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

# ==============================
# PAYMENT METHOD ANALYTICS
# ==============================
def get_payment_method_report(start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT payment_method, IFNULL(SUM(amount), 0)
        FROM transactions
        WHERE 1=1
    """
    params = []

    # 🔥 Optional date filters (future ready)
    if start_date:
        query += " AND DATE(payment_date) >= ?"
        params.append(start_date)

    if end_date:
        query += " AND DATE(payment_date) <= ?"
        params.append(end_date)

    query += " GROUP BY payment_method"

    cursor.execute(query, params)
    data = cursor.fetchall()

    conn.close()
    return data

# ==============================
# MONTHLY ARPU TREND
# ==============================
def get_monthly_arpu_trend():
    conn = get_connection()
    cursor = conn.cursor()

    # Get monthly revenue
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', payment_date) as month,
            IFNULL(SUM(amount), 0)
        FROM transactions
        GROUP BY month
    """)
    revenue_data = cursor.fetchall()

    # Get active customers count
    cursor.execute("""
    SELECT COUNT(*)
    FROM customers
    WHERE status = 'ACTIVE'
""")
    active_users = cursor.fetchone()[0] or 0

    conn.close()

    if active_users == 0:
        return []

    result = []
    for month, revenue in revenue_data:
        if month:
            arpu = revenue / active_users
            result.append((month, arpu))

    return sorted(result)

# ==============================
# CURRENT MONTH ARPU (CARD)
# ==============================
def calculate_monthly_arpu():
    conn = get_connection()
    cursor = conn.cursor()

    # Count ACTIVE customers
    cursor.execute("""
    SELECT COUNT(*)
    FROM customers
    WHERE status = 'ACTIVE'
""")
    active_customers = cursor.fetchone()[0] or 0

    if active_customers == 0:
        conn.close()
        return 0

    # Current month revenue
    current_month = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM transactions
        WHERE strftime('%Y-%m', payment_date) = ?
    """, (current_month,))
    revenue = cursor.fetchone()[0] or 0

    conn.close()

    return round(revenue / active_customers, 2)