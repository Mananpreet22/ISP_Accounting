import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from customers import add_customer, get_all_customers, delete_customer, get_customer_by_id, update_customer
from billing import create_or_update_bill, get_bills, mark_bill_paid, update_unpaid_bill, generate_monthly_bills_for_all, increment_bill_reminder
import webbrowser
import urllib.parse
from pdf_utils import generate_bill_pdf
import os
from backup_utils import backup_database
from db_migrations import apply_migrations
from accounting import add_expense, get_today_profit, get_all_expenses
from accounting import get_current_month_summary
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")
from accounting import get_monthly_arpu_trend
from excel_utils import export_transactions_to_excel, export_monthly_report
from customers import check_duplicate_phone
from db_setup import setup_database
from tkinter import simpledialog 




def generate_selected_bill_pdf():
    row = get_selected_bill_row()
    if not row:
        messagebox.showerror("Error", "Select a bill")
        return

    path = generate_bill_pdf(row)
    messagebox.showinfo("PDF Generated", f"Saved at:\n{path}")
    os.startfile(path)  # opens PDF automatically on Windows


# =========================
# App Setup
# =========================
root = tk.Tk()
root.title("ISP Billing Dashboard")
root.geometry("1250x750")
root.configure(bg="#f0f2f5")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
style.configure("Treeview", rowheight=25, font=("Arial", 10))

import sys
import os

def get_db_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "isp_billing.db")
    else:
        return os.path.join(os.path.dirname(__file__), "isp_billing.db")

DB_NAME = get_db_path()

# ✅ CREATE DB IF NOT EXISTS
if not os.path.exists(DB_NAME):
    print("Database not found, creating...")
    setup_database(DB_NAME)

# ✅ ALWAYS ENSURE TABLES EXIST
setup_database(DB_NAME)

# ✅ APPLY MIGRATIONS
apply_migrations(DB_NAME)

# ✅ BACKUP AFTER EVERYTHING READY
backup_database(DB_NAME)

# =========================
# App State
# =========================
selected_customer_id_for_edit = None
selected_bill_id_for_edit = None
selected_expense_id_for_edit = None

# =========================
# Navigation
# =========================
def show_frame(frame):
    frame.tkraise()

# =========================
# Metrics
# =========================
total_customers_var = tk.IntVar()
total_paid_var = tk.IntVar()
total_unpaid_var = tk.IntVar()
total_revenue_var = tk.DoubleVar()
monthly_arpu_var = tk.DoubleVar()

def refresh_metrics():
    customers = get_all_customers()
    bills = get_bills()

    total_customers_var.set(len(customers))
    total_paid_var.set(len([b for b in bills if (b[5] or "").upper() == "PAID"]))
    total_unpaid_var.set(len([b for b in bills if (b[5] or "").upper() == "UNPAID"]))
    total_revenue_var.set(sum([float(b[3] or 0) for b in bills if (b[5] or "").upper() == "PAID"]))
    from accounting import calculate_monthly_arpu
    arpu = calculate_monthly_arpu()
    monthly_arpu_var.set(arpu)
    draw_arpu_chart()
    refresh_revenue_expense_chart()

# funtion for dashbord revnue chart 

def refresh_revenue_expense_chart():
    from accounting import get_monthly_profit

    for widget in rev_exp_chart_frame.winfo_children():
        widget.destroy()

    data = get_monthly_profit()
    if not data:
        tk.Label(rev_exp_chart_frame, text="No data available").pack()
        return

    data.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m"))

    months = [d[0] for d in data]
    income = [d[1] for d in data]
    expense = [d[2] for d in data]
    fig, ax = plt.subplots(figsize=(9,4))

    ax.plot(months, income, marker="o", label="Income")
    ax.plot(months, expense, marker="o", label="Expense")

    ax.set_title("Revenue vs Expense Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount")
    ax.legend()
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45, ha='right')
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=rev_exp_chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    plt.close(fig)



# =========================
# Customers
# =========================
def clear_customer_fields():
    global selected_customer_id_for_edit
    selected_customer_id_for_edit = None
    entry_name.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    entry_email.delete(0, tk.END)
    entry_address.delete(0, tk.END)
    entry_amount.delete(0, tk.END)
    btn_save_customer.configure(text="Add Customer", bg="#4CAF50", fg="white")

import re

def validate_customer(name, phone, email, amount):
    # Name check
    if not name.strip():
        return "Name is required"

    # Phone: only digits + exactly 10 digits
    phone = phone.strip()
    if not phone.isdigit() or len(phone) != 10:
        return "Phone must be exactly 10 digits"

    # Email (optional)
    if email:
        email = email.strip()
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, email):
            return "Invalid email format"

    # Amount validation
    if not amount.strip():
        return "Amount is required"

    try:
        float(amount)
    except ValueError:
        return "Amount must be a number"

    return None

def save_or_update_customer():
    global selected_customer_id_for_edit

    name = entry_name.get().strip()
    phone = entry_phone.get().strip()
    email = entry_email.get().strip()
    address = entry_address.get().strip()
    plan = plan_var.get().strip()
    amount = entry_amount.get().strip()
    status = customer_status_var.get()

    # =========================
    # VALIDATION
    # =========================
    error = validate_customer(name, phone, email, amount)
    if error:
        messagebox.showerror("Validation Error", error)
        return

    try:
        amount = float(amount)

        # =========================
        # ADD MODE
        # =========================
        if selected_customer_id_for_edit is None:
            add_customer(name, phone, email, address, plan, amount, status)
            messagebox.showinfo("Success", "Customer added")

        # =========================
        # UPDATE MODE
        # =========================
        else:
            update_customer(
                selected_customer_id_for_edit,
                name, phone, email, address, plan, amount, status
            )
            messagebox.showinfo("Success", "Customer updated")

    except Exception as e:
        messagebox.showerror("Error", f"Something went wrong:\n{e}")
        return

    # =========================
    # REFRESH UI
    # =========================
    clear_customer_fields()
    load_customers_table()
    refresh_metrics()
    load_customer_dropdown()

def delete_selected_customer_ui():
    selected = customers_tree.selection()
    if not selected:
        messagebox.showerror("Error", "Select a customer")
        return
    customer_id = int(customers_tree.item(selected[0], "values")[0])
    if messagebox.askyesno("Confirm", "Delete this customer?"):
        if not delete_customer(customer_id):
            messagebox.showerror("Error", "Cannot delete customer with existing bills")
            return
        clear_customer_fields()
        load_customers_table()
        refresh_metrics()
        load_customer_dropdown()

def on_customer_select(event=None):
    global selected_customer_id_for_edit
    selected = customers_tree.selection()
    if not selected:
        return
    customer_id = int(customers_tree.item(selected[0], "values")[0])
    row = get_customer_by_id(customer_id)
    if not row:
        return

    selected_customer_id_for_edit = customer_id

    # clear fields but don't reset selected_customer_id_for_edit
    entry_name.delete(0, tk.END)
    entry_phone.delete(0, tk.END)
    entry_email.delete(0, tk.END)
    entry_address.delete(0, tk.END)
    plan_var.set("")
    entry_amount.delete(0, tk.END)

    entry_name.insert(0, row[1] or "")
    entry_phone.insert(0, row[2] or "")
    entry_email.insert(0, row[3] or "")
    entry_address.insert(0, row[4] or "")
    plan_var.set(row[5] or "")
    entry_amount.insert(0, str(row[6] or ""))
    customer_status_var.set(row[7] or "ACTIVE")
    btn_save_customer.configure(text="Save Changes", bg="#FF9800", fg="white")


def load_customers_table():
    for row in customers_tree.get_children():
        customers_tree.delete(row)

    q = customer_search_var.get().strip().lower()
    customers = get_all_customers()

    if q:
        customers = [
            c for c in customers
            if q in str(c[1]).lower() or q in str(c[2]).lower()
        ]

    for c in customers:
        status = c[7] if len(c) > 7 else "ACTIVE"

        customers_tree.insert(
            "",
            "end",
            values=(
                c[0],
                c[1],
                c[2],
                c[3] or "",
                c[4] or "",
                c[5] or "",
                c[6] or 0,
                status
            ),
            tags=(status,)
        )

def load_customer_dropdown():
    customer_menu["menu"].delete(0, "end")
    customers = get_all_customers()
    if not customers:
        selected_customer.set(0)
        return
    selected_customer.set(customers[0][0])
    for c in customers:
        customer_menu["menu"].add_command(label=f"{c[0]} - {c[1]}", command=lambda cid=c[0]: selected_customer.set(cid))



# =========================
# Billing
# =========================
def generate_bill():
    customer_id = selected_customer.get()
    amount = entry_bill_amount.get().strip()
    due = entry_due_date.get().strip()

    if not customer_id or not amount or not due:
        messagebox.showerror("Error", "Select customer, enter amount & due date")
        return

    #  Amount validation
    try:
        amount = float(amount)
    except ValueError:
        messagebox.showerror("Error", "Amount must be a number")
        return

    create_or_update_bill(customer_id, amount, due)
    messagebox.showinfo("Success", "Bill generated/updated")
    load_bills_table()
    refresh_metrics()


def edit_selected_bill():
    global selected_bill_id_for_edit
    row = bills_tree.selection()
    if not row:
        messagebox.showerror("Error", "Select a bill")
        return
    bill_id, status = int(bills_tree.item(row[0], "values")[0]), bills_tree.item(row[0], "values")[5]
    if status.upper() == "PAID":
        messagebox.showinfo("Info", "Paid bills cannot be edited")
        return

    selected_bill_id_for_edit = bill_id
    entry_bill_amount.delete(0, tk.END)
    entry_bill_amount.insert(0, bills_tree.item(row[0], "values")[3])
    entry_due_date.delete(0, tk.END)
    entry_due_date.insert(0, bills_tree.item(row[0], "values")[4])
    btn_save_bill.configure(text=f"Save Bill#{bill_id} Changes", bg="#FF9800")

def save_bill_changes():
    global selected_bill_id_for_edit

    if not selected_bill_id_for_edit:
        generate_bill()
        return

    amount = entry_bill_amount.get().strip()
    due = entry_due_date.get().strip()

    if not amount or not due:
        messagebox.showerror("Error", "Amount and Due Date required")
        return

    #  Amount validation
    try:
        amount = float(amount)
    except ValueError:
        messagebox.showerror("Error", "Amount must be a number")
        return

    if messagebox.askyesno("Confirm", f"Update Bill#{selected_bill_id_for_edit}?"):
        update_unpaid_bill(selected_bill_id_for_edit, amount, due)
        messagebox.showinfo("Success", f"Bill#{selected_bill_id_for_edit} updated")

        selected_bill_id_for_edit = None
        btn_save_bill.configure(text="Generate/Update Bill", bg="#3498db")
        load_bills_table()
        refresh_metrics()


# recipt no popup

def ask_receipt_popup():
    popup = tk.Toplevel(root)
    popup.title("Enter Receipt Number")

    popup.update_idletasks()   

    # Centering logic here
    root_x = root.winfo_rootx()
    root_y = root.winfo_rooty()
    root_width = root.winfo_width()
    root_height = root.winfo_height()

    popup_width = 320
    popup_height = 180

    x = root_x + (root_width // 2) - (popup_width // 2)
    y = root_y + (root_height // 2) - (popup_height // 2)

    popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

    popup.configure(bg="#f4f6f9")
    popup.resizable(False, False)

    # Center window
    popup.transient(root)
    popup.grab_set()

    tk.Label(
        popup,
        text="Enter Receipt Number",
        font=("Segoe UI", 11, "bold"),
        bg="#f4f6f9"
    ).pack(pady=15)

    entry = tk.Entry(popup, font=("Segoe UI", 11), justify="center")
    entry.pack(pady=5, ipadx=10, ipady=3)
    entry.focus()

    result = {"value": None}

    def submit():
        val = entry.get().strip()
        if not val:
            messagebox.showerror("Error", "Receipt number required")
            return
        result["value"] = val
        popup.destroy()

    def cancel():
        popup.destroy()

    btn_frame = tk.Frame(popup, bg="#f4f6f9")
    btn_frame.pack(pady=15)

    tk.Button(
        btn_frame,
        text="OK",
        width=10,
        bg="#2ecc71",
        fg="white",
        command=submit
    ).grid(row=0, column=0, padx=5)

    tk.Button(
        btn_frame,
        text="Cancel",
        width=10,
        bg="#e74c3c",
        fg="white",
        command=cancel
    ).grid(row=0, column=1, padx=5)

    popup.wait_window()
    return result["value"]


 

def mark_selected_bill_paid():
    row = bills_tree.selection()
    if not row:
        messagebox.showerror("Error", "Select a bill")
        return

    bill_id = int(bills_tree.item(row[0], "values")[0])
    status = bills_tree.item(row[0], "values")[5]

    if status.upper() == "PAID":
        messagebox.showinfo("Info", "Bill already paid")
        return

  
    receipt_no = ask_receipt_popup()

   
    if not receipt_no:
        return


    if messagebox.askyesno("Confirm", f"Mark Bill#{bill_id} as PAID?"):
        mark_bill_paid(
            bill_id,
            payment_method_var.get(),
            receipt_no.strip()
        )

        load_bills_table()
        messagebox.showinfo("Success", "Payment recorded")

        refresh_metrics()
        refresh_dashboard_chart()
        refresh_payment_analytics()

def refresh_dashboard_chart():
    for widget in revenue_chart_frame.winfo_children():
        widget.destroy()

    bills = get_bills()
    revenue_by_month = {}

    for b in bills:
        month = b[2]
        status = (b[5] or "").upper()

        if status != "PAID":
            continue

        try:
            amount = float(b[3])
        except:
            continue

        revenue_by_month[month] = revenue_by_month.get(month, 0) + amount

    if not revenue_by_month:
        tk.Label(revenue_chart_frame, text="No data available").pack()
        return

    months = sorted(revenue_by_month.keys(), key=lambda x: datetime.strptime(x, "%Y-%m"))
    values = [revenue_by_month[m] for m in months]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(months, values, marker="o")
    ax.set_title("Monthly Paid Revenue")
    ax.set_ylabel("₹ Revenue")
    ax.set_xlabel("Month")
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45, ha='right')
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=revenue_chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    plt.close(fig)

def generate_all_bills():
    due_date = entry_due_date.get().strip()
    if not due_date:
        messagebox.showerror("Error", "Enter due date")
        return
    count = generate_monthly_bills_for_all(due_date)
    messagebox.showinfo("Done", f"{count} bills generated/updated")
    load_bills_table()
    refresh_metrics()

def load_bills_table():
    for row in bills_tree.get_children():
        bills_tree.delete(row)

    q = bill_search_var.get().strip().lower()
    bills = get_bills()
    status_filter = bill_status_filter.get()

    if status_filter == "UNPAID":
        bills = [b for b in bills if (b[5] or "").upper() == "UNPAID"]
    elif status_filter == "PAID":
        bills = [b for b in bills if (b[5] or "").upper() == "PAID"]

    if q:
        bills = [b for b in bills if q in str(b[1]).lower() or q in str(b[0]).lower()]

    today = datetime.today().date()

    for b in bills:
        bill_id, customer, month, amount, due, status, method, receipt_no, paid_date, reminder_count, last_reminder = b

        tag = "unpaid"

        if status.upper() == "PAID":
            tag = "paid"
        else:
            try:
                due_date = datetime.strptime(due, "%Y-%m-%d").date()
                days_left = (due_date - today).days

                if days_left < 0:
                    tag = "overdue"
                elif days_left <= 2:
                    tag = "due_soon"
            except:
                pass

        bills_tree.insert(
            "",
            "end",
            values=(
    bill_id, customer, month, amount, due,
    status, method, receipt_no or "-",
    paid_date, reminder_count or 0,
    last_reminder or "-"
),
            tags=(tag,)
        )

    update_payment_button_state()


def get_selected_bill_row():
    selected = bills_tree.selection()
    return bills_tree.item(selected[0], "values") if selected else None

def update_payment_button_state(*args):
    row = get_selected_bill_row()
    if not row:
        btn_mark_paid.configure(state="disabled")
        btn_edit_bill.configure(state="disabled")
        btn_whatsapp.configure(state="disabled")
        btn_pdf.configure(state="disabled")
        return

    status = str(row[5]).upper()

    btn_mark_paid.configure(state="normal" if status=="UNPAID" else "disabled")
    btn_edit_bill.configure(state="normal" if status=="UNPAID" else "disabled")
    btn_whatsapp.configure(state="normal" if status=="UNPAID" else "disabled")
    btn_pdf.configure(state="normal")  

def send_whatsapp_reminder():
    row = get_selected_bill_row()
    if not row:
        messagebox.showerror("Error", "Select a bill")
        return

    bill_id, customer, month, amount, due, status = row[:6]

    if str(status).upper() == "PAID":
        messagebox.showinfo("Info", "Bill already paid")
        return

    # ======================
    # Find customer phone
    # ======================
    phone = None
    for c in get_all_customers():
        if c[1] == customer:
            phone = c[2]
            break

    if not phone:
        messagebox.showerror("Error", "Customer phone not found")
        return

    # ======================
    # UPI PAYMENT LINK
    # ======================
    upi_id = "UPI@id"   # 🔴 CHANGE IF NEEDED
    payee_name = "My Broadband"
    note = f"Internet Bill - {month}"

    upi_link = (
        f"upi://pay?"
        f"pa={upi_id}&"
        f"pn={urllib.parse.quote(payee_name)}&"
        f"am={amount}&"
        f"cu=INR&"
        f"tn={urllib.parse.quote(note)}"
    )

    # ======================
    # WhatsApp Message
    # ======================
    message = (
        f"Hello {customer},\n\n"
        f"📄 *Internet Bill Reminder*\n\n"
        f"📅 Month: {month}\n"
        f"💰 Amount: ₹{amount}\n"
        f"⏰ Due Date: {due}\n\n"
        f"👉 *Pay instantly using UPI:*\n"
        f"{upi_link}\n\n"
        f"Or pay using UPI number:\n"
        f"900000070\n\n" # CHANGE IF NEEDED
        f"Thank you for choosing *My Broadband* 🙏"
    )

    # ======================
    # Open WhatsApp
    # ======================
    phone = str(phone).replace(" ", "").replace("-", "")
    if not phone.startswith("91"):
        phone = "91" + phone

    url = f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
    webbrowser.open(url)

    # ======================
    # TRACK REMINDER (DB)
    # ======================
    today = datetime.now().strftime("%Y-%m-%d")
    increment_bill_reminder(bill_id, today)

    messagebox.showinfo("Success", "WhatsApp opened & reminder tracked")
    load_bills_table()


def send_whatsapp_link(phone, message):
    phone = str(phone).replace(" ", "").replace("-", "")
    if not phone.startswith("91"):
        phone = "91" + phone  # India country code

    encoded_msg = urllib.parse.quote(message)
    url = f"https://wa.me/{phone}?text={encoded_msg}"
    webbrowser.open(url)

# mothly data

def show_monthly_revenue_graph():
    bills = get_bills()
    revenue_by_month = {}

    for b in bills:
        month = b[2]
        raw_amount = b[3]
        status = (b[5] or "").upper()

        if status != "PAID":
            continue

        try:
            amount = float(raw_amount)
        except (ValueError, TypeError):
            # Skip invalid amounts like "sdfg"
            continue

        revenue_by_month[month] = revenue_by_month.get(month, 0) + amount

    if not revenue_by_month:
        messagebox.showinfo("Info", "No valid paid bills to show")
        return

    months = sorted(
    revenue_by_month.keys(),
    key=lambda x: datetime.strptime(x, "%Y-%m")
         )
    revenues = [revenue_by_month[m] for m in months]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(8, 4))
    plt.bar(months, revenues)
    plt.xlabel("Month")
    plt.ylabel("Revenue (₹)")
    plt.title("Monthly Revenue Report")
    plt.tight_layout()
    plt.show()

# mothly data profit accouting 

def show_monthly_profit_graph():
    from accounting import get_monthly_profit
    data = get_monthly_profit()
    data.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m"))

    if not data:
        messagebox.showinfo("Info", "No data available")
        return

    months = [d[0] for d in data]
    income = [d[1] for d in data]
    expenses = [d[2] for d in data]
    profit = [d[3] for d in data]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(8,4))
    plt.plot(months, income, marker="o", label="Income")
    plt.plot(months, expenses, marker="o", label="Expenses")
    plt.plot(months, profit, marker="o", label="Profit")

    plt.legend()
    plt.title("Monthly ISP Profit")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


#### pie chart 

def show_expense_category_chart():
    from accounting import get_expense_category_report
    data = get_expense_category_report()

    if not data:
        messagebox.showinfo("Info", "No expenses found")
        return

    categories = [d[0] for d in data]
    amounts = [d[1] for d in data]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(6,6))
    plt.pie(amounts, labels=categories, autopct="%1.1f%%")
    plt.title("Expense Categories")
    plt.show()
    plt.tight_layout()

# Edit section for expense 

def on_expense_select(event=None):
    global selected_expense_id_for_edit

    selected = expenses_tree.selection()
    if not selected:
        return

    values = expenses_tree.item(selected[0], "values")

    selected_expense_id_for_edit = values[0]

    # Fill form fields
    entry_exp_category.delete(0, tk.END)
    entry_exp_desc.delete(0, tk.END)
    entry_exp_amount.delete(0, tk.END)
    entry_exp_date.delete(0, tk.END)

    entry_exp_category.insert(0, values[1])
    entry_exp_desc.insert(0, values[2])
    entry_exp_amount.insert(0, values[3])
    entry_exp_date.set_date(values[5])

    exp_method_var.set(values[4])
    btn_save_expense.config(text="Update Expense", bg="#f39c12")

# Pyment mathod anylytics 
def show_payment_method_chart():
    from accounting import get_payment_method_report

    data = get_payment_method_report()

    if not data:
        messagebox.showinfo("Info", "No payment data available")
        return

    methods = [d[0] for d in data]
    amounts = [d[1] for d in data]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(6,6))
    plt.pie(amounts, labels=methods, autopct="%1.1f%%")
    plt.title("Payment Method Analytics")
    plt.show()
    plt.tight_layout()

# chart funtion funtion for dashbord 

def refresh_customer_status_chart():
    from customers import get_customer_status_report

    for widget in status_chart_frame.winfo_children():
        widget.destroy()

    data = get_customer_status_report()

    if not data:
        tk.Label(status_chart_frame, text="No customer data").pack()
        return

    labels = [d[0] for d in data]
    values = [d[1] for d in data]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.set_title("Customer Status Distribution")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=status_chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    plt.close(fig)


# =========================
# UI
# =========================
# =========================
# SIDEBAR
# =========================

sidebar = tk.Frame(root, bg="#1f2d3d", width=220)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

# Store buttons for highlight control
sidebar_buttons = {}

def switch_page(name):
    show_frame(pages[name])

    # Reset all buttons
    for btn in sidebar_buttons.values():
        btn.config(bg="#1f2d3d")

    # Highlight active one
    sidebar_buttons[name].config(bg="#16a085")

def create_sidebar_button(text):
    btn = tk.Button(
        sidebar,
        text="  " + text,
        anchor="w",
        bg="#1f2d3d",
        fg="white",
        activebackground="#16a085",
        activeforeground="white",
        relief="flat",
        bd=0,
        height=2,
        font=("Segoe UI", 10),
        command=lambda: switch_page(text)
    )

    btn.pack(fill="x", padx=10, pady=4)
    sidebar_buttons[text] = btn

# Create buttons
for text in ["Dashboard", "Customers", "Billing", "Accounting"]:
    create_sidebar_button(text)


container = tk.Frame(root, bg="#f0f2f5")
container.pack(side="right", fill="both", expand=True)

dashboard_page = tk.Frame(container, bg="#f0f2f5")
dashboard_page.configure(bg="#f4f6f9")

main_dashboard_frame = tk.Frame(dashboard_page, bg="#f4f6f9")
main_dashboard_frame.pack(fill="both", expand=True, padx=20, pady=20)
customers_page = tk.Frame(container, bg="#f0f2f5")
billing_page = tk.Frame(container, bg="#f0f2f5")
# =========================
# SCROLLABLE ACCOUNTING PAGE
# =========================
accounting_page = tk.Frame(container, bg="#f0f2f5")

# Canvas
accounting_canvas = tk.Canvas(accounting_page, bg="#f0f2f5")
accounting_canvas.pack(side="left", fill="both", expand=True)

# Scrollbar
accounting_scrollbar = ttk.Scrollbar(
    accounting_page,
    orient="vertical",
    command=accounting_canvas.yview
)
accounting_scrollbar.pack(side="right", fill="y")

accounting_canvas.configure(yscrollcommand=accounting_scrollbar.set)

# Inner frame (THIS will hold everything)
accounting_inner = tk.Frame(accounting_canvas, bg="#f0f2f5")

accounting_canvas.create_window((0, 0), window=accounting_inner, anchor="nw")

# Auto scroll region
def _configure_accounting(event):
    accounting_canvas.configure(
        scrollregion=accounting_canvas.bbox("all")
    )

accounting_inner.bind("<Configure>", _configure_accounting)

# Mouse wheel scroll
def _on_mousewheel(event):
    accounting_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

accounting_canvas.bind("<Enter>", lambda e: accounting_canvas.bind_all("<MouseWheel>", _on_mousewheel))
accounting_canvas.bind("<Leave>", lambda e: accounting_canvas.unbind_all("<MouseWheel>"))


pages = {
    "Dashboard": dashboard_page,
    "Customers": customers_page,
    "Billing": billing_page,
    "Accounting": accounting_page
}
for page in pages.values():
    page.place(relwidth=1, relheight=1)

# Dashboard Cards
def create_card(parent, title, variable, color):
    card = tk.Frame(parent, bg="white", highlightthickness=1, highlightbackground="#e0e0e0")

    tk.Label(
        card,
        text=title,
        font=("Segoe UI", 10),
        bg="white",
        fg="#555"
    ).pack(anchor="w", padx=15, pady=(15, 5))

    tk.Label(
        card,
        textvariable=variable,
        font=("Segoe UI", 20, "bold"),
        bg="white",
        fg=color
    ).pack(anchor="w", padx=15, pady=(0, 15))

    return card

# =========================
# dashbord KPI SECTION
# =========================

kpi_frame = tk.Frame(main_dashboard_frame, bg="#f4f6f9")
kpi_frame.pack(fill="x", padx=20, pady=10)

for i in range(5):
    kpi_frame.columnconfigure(i, weight=1)

card1 = create_card(kpi_frame, "Total Customers", total_customers_var, "#3498db")
card2 = create_card(kpi_frame, "Paid Bills", total_paid_var, "#2ecc71")
card3 = create_card(kpi_frame, "Unpaid Bills", total_unpaid_var, "#e74c3c")
card4 = create_card(kpi_frame, "Monthly Revenue", total_revenue_var, "#9b59b6")
card5 = create_card(kpi_frame, "ARPU", monthly_arpu_var, "#f39c12")

card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
card4.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
card5.grid(row=0, column=4, padx=10, pady=10, sticky="nsew")

# =========================
# QUICK ACTIONS
# =========================
quick_frame = tk.Frame(main_dashboard_frame, bg="white")
quick_frame.pack(fill="x", pady=(0,20))

tk.Button(
    quick_frame,
    text="➕ Add Customer",
    bg="#3498db",
    fg="white",
    width=18,
    command=lambda: show_frame(customers_page)
).pack(side="left", padx=10)

tk.Button(
    quick_frame,
    text="🧾 Generate Bill",
    bg="#2ecc71",
    fg="white",
    width=18,
    command=lambda: show_frame(billing_page)
).pack(side="left", padx=10)

tk.Button(
    quick_frame,
    text="💰 Add Expense",
    bg="#e67e22",
    fg="white",
    width=18,
    command=lambda: show_frame(accounting_page)
).pack(side="left", padx=10)

#analytics frams 
analytics_frame = tk.Frame(main_dashboard_frame, bg="#f4f6f9")
analytics_frame.pack(fill="both", expand=True)

analytics_frame.columnconfigure(0, weight=1)
analytics_frame.columnconfigure(1, weight=1)
analytics_frame.rowconfigure(0, weight=1)
analytics_frame.rowconfigure(1, weight=1)

# =========================
# DASHBOARD REVENUE CHART
# =========================
revenue_frame = tk.Frame(analytics_frame, bg="white")
revenue_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

tk.Label(
    revenue_frame,
    text="Monthly Revenue",
    font=("Segoe UI", 12, "bold"),
    bg="white"
).pack(anchor="w", padx=15, pady=10)

revenue_chart_frame = tk.Frame(revenue_frame, bg="white")
revenue_chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

# =========================
# DASHBOARD ARPU TREND
# =========================
arpu_frame = tk.Frame(analytics_frame, bg="white")
arpu_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

tk.Label(
    arpu_frame,
    text="ARPU Trend",
    font=("Segoe UI", 12, "bold"),
    bg="white"
).pack(anchor="w", padx=15, pady=10)

arpu_chart_frame = tk.Frame(arpu_frame, bg="white")
arpu_chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

def draw_arpu_chart():
    for widget in arpu_chart_frame.winfo_children():
        widget.destroy()

    data = get_monthly_arpu_trend()

    if not data:
        tk.Label(arpu_chart_frame, text="No ARPU data available").pack()
        return

    data.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m"))
    months = [row[0] for row in data]
    arpu_values = [row[1] for row in data]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(months, arpu_values, marker="o")
    ax.set_xlabel("Month")
    ax.set_ylabel("ARPU")
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, rotation=45, ha='right')
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=arpu_chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    plt.close(fig)

# =========================
# REVENUE VS EXPENSE CHART
# =========================
rev_exp_frame = tk.Frame(analytics_frame, bg="white")
rev_exp_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

tk.Label(
    rev_exp_frame,
    text="Revenue vs Expense",
    font=("Segoe UI", 12, "bold"),
    bg="white"
).pack(anchor="w", padx=15, pady=10)

rev_exp_chart_frame = tk.Frame(rev_exp_frame, bg="white")
rev_exp_chart_frame.pack(fill="both", expand=True, padx=10, pady=10)


# =========================
# CUSTOMER STATUS OVERVIEW
# =========================
status_frame = tk.Frame(analytics_frame, bg="white")
status_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

tk.Label(
    status_frame,
    text="Customer Status",
    font=("Segoe UI", 12, "bold"),
    bg="white"
).pack(anchor="w", padx=15, pady=10)

status_chart_frame = tk.Frame(status_frame, bg="white")
status_chart_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Customers Page
cust_form = tk.LabelFrame(customers_page, text="Customer Form")
cust_form.pack(fill="x", padx=10, pady=10)
def add_labeled_entry(parent, label):
    row = tk.Frame(parent)
    row.pack(fill="x", pady=2)
    tk.Label(row, text=label, width=15, anchor="w").pack(side="left")
    e = tk.Entry(row)
    e.pack(side="left", fill="x", expand=True)
    return e
entry_name = add_labeled_entry(cust_form, "Name")
entry_phone = add_labeled_entry(cust_form, "Phone")
entry_email = add_labeled_entry(cust_form, "Email")
entry_address = add_labeled_entry(cust_form, "Address")
# =========================
# PLAN DROPDOWN
# =========================

plan_data = {
    "30 Mbps - 1 Month": 500,
    "50 Mbps - 1 Month": 700,
    "100 Mbps - 1 Month": 1000,
    "30 Mbps - 6 Months": 2700,
    "50 Mbps - 6 Months": 3900,
    "100 Mbps - 6 Months": 5500
}

plan_var = tk.StringVar()

plan_row = tk.Frame(cust_form)
plan_row.pack(fill="x", pady=2)

tk.Label(plan_row, text="Plan", width=15, anchor="w").pack(side="left")

plan_dropdown = ttk.Combobox(
    plan_row,
    textvariable=plan_var,
    values=list(plan_data.keys()),
    state="readonly"
)
plan_dropdown.pack(side="left", fill="x", expand=True)
def on_plan_select(event=None):
    selected_plan = plan_var.get()
    if selected_plan in plan_data:
        entry_amount.delete(0, tk.END)
        entry_amount.insert(0, plan_data[selected_plan])
plan_dropdown.bind("<<ComboboxSelected>>", on_plan_select)
entry_amount = add_labeled_entry(cust_form, "Amount")
# for status 
status_row = tk.Frame(cust_form)
status_row.pack(fill="x", pady=2)

tk.Label(status_row, text="Status", width=15, anchor="w").pack(side="left")

customer_status_var = tk.StringVar(value="ACTIVE")

tk.OptionMenu(
    status_row,
    customer_status_var,
    "ACTIVE",
    "INACTIVE",
    "SUSPENDED"
).pack(side="left", fill="x", expand=True)

btn_row = tk.Frame(cust_form)
btn_row.pack(fill="x", pady=5)
btn_save_customer = tk.Button(btn_row, text="Add Customer", bg="#4CAF50", fg="white", command=save_or_update_customer)
btn_save_customer.pack(side="left", padx=5)
tk.Button(btn_row, text="Delete Selected", bg="#e74c3c", fg="white", command=delete_selected_customer_ui).pack(side="left", padx=5)
tk.Button(btn_row, text="Clear", command=clear_customer_fields).pack(side="left", padx=5)

search_row = tk.Frame(customers_page)
search_row.pack(fill="x", padx=10, pady=5)
tk.Label(search_row, text="Search:").pack(side="left")
customer_search_var = tk.StringVar()
tk.Entry(search_row, textvariable=customer_search_var).pack(side="left", fill="x", expand=True, padx=5)
tk.Button(search_row, text="Go", command=load_customers_table).pack(side="left", padx=5)
tk.Button(search_row, text="Reset", command=lambda: (customer_search_var.set(""), load_customers_table())).pack(side="left", padx=5)

customers_frame = tk.Frame(customers_page)
customers_frame.pack(fill="both", expand=True, padx=10, pady=5)
customers_tree = ttk.Treeview(
    customers_frame,
    columns=("id", "name", "phone", "email", "address", "plan", "amount", "status"),
    show="headings"
)

for col, w in [
    ("id",60),
    ("name",180),
    ("phone",140),
    ("email",200),
    ("address",200),
    ("plan",120),
    ("amount",100),
    ("status",100)
]:
    customers_tree.heading(col, text=col.title())
    customers_tree.column(col, width=w)
cust_scroll = ttk.Scrollbar(customers_frame, orient="vertical", command=customers_tree.yview)
customers_tree.configure(yscrollcommand=cust_scroll.set)
customers_tree.pack(side="left", fill="both", expand=True)
cust_scroll.pack(side="right", fill="y")
customers_tree.bind("<<TreeviewSelect>>", on_customer_select)
customers_tree.tag_configure("ACTIVE", background="#d4edda")     # green
customers_tree.tag_configure("SUSPENDED", background="#fff3cd")  # yellow
customers_tree.tag_configure("INACTIVE", background="#f8d7da")   # red

# Billing Page
bill_form = tk.LabelFrame(billing_page, text="Billing Form")
bill_form.pack(fill="x", padx=10, pady=10)
row1 = tk.Frame(bill_form)
row1.pack(fill="x", pady=2)
tk.Label(row1, text="Customer:", width=12).pack(side="left")
selected_customer = tk.IntVar()
customer_menu = tk.OptionMenu(row1, selected_customer, "")
customer_menu.pack(side="left", fill="x", expand=True)
row2 = tk.Frame(bill_form)
row2.pack(fill="x", pady=2)
tk.Label(row2, text="Amount:", width=12).pack(side="left")
entry_bill_amount = tk.Entry(row2)
entry_bill_amount.pack(side="left", fill="x", expand=True)
row3 = tk.Frame(bill_form)
row3.pack(fill="x", pady=2)
tk.Label(row3, text="Due Date:", width=12).pack(side="left")
entry_due_date = DateEntry(
    row3,
    width=12,
    background="darkblue",
    foreground="white",
    borderwidth=2,
    date_pattern="yyyy-mm-dd"
)
entry_due_date.pack(side="left", fill="x", expand=True)
btn_save_bill = tk.Button(bill_form, text="Generate/Update Bill", bg="#3498db", fg="white", command=save_bill_changes)
btn_save_bill.pack(pady=5)
tk.Button(bill_form, text="Generate All Bills for Month", bg="#9b59b6", fg="white", command=generate_all_bills).pack(pady=5)

# Billing Search/Filter
filter_row = tk.Frame(billing_page)
filter_row.pack(fill="x", padx=10, pady=5)
tk.Label(filter_row, text="Filter:").pack(side="left")
bill_status_filter = tk.StringVar(value="ALL")
tk.OptionMenu(filter_row, bill_status_filter, "ALL", "UNPAID", "PAID", command=lambda _: load_bills_table()).pack(side="left", padx=5)
tk.Label(filter_row, text="Search:").pack(side="left", padx=5)
bill_search_var = tk.StringVar()
tk.Entry(filter_row, textvariable=bill_search_var).pack(side="left", fill="x", expand=True, padx=5)
tk.Button(filter_row, text="Go", command=load_bills_table).pack(side="left", padx=5)
tk.Button(filter_row, text="Reset", command=lambda: (bill_search_var.set(""), load_bills_table())).pack(side="left", padx=5)

# Bills Table
bills_frame = tk.Frame(billing_page)
bills_frame.pack(fill="both", expand=True, padx=10, pady=5)
bills_tree = ttk.Treeview(
    bills_frame,
    columns=(
    "id","customer","month","amount","due",
    "status","method","receipt","paid_date",
    "reminders","last_reminder"
),
    show="headings"
)
for col, w in [
    ("id",70),("customer",160),("month",100),
    ("amount",100),("due",100),("status",90),
    ("method",90),("receipt",90),("paid_date",110),
    ("reminders",90),("last_reminder",120)
]:
    bills_tree.heading(col, text=col.title())
    bills_tree.column(col,width=w)
bill_scroll = ttk.Scrollbar(bills_frame, orient="vertical", command=bills_tree.yview)
bills_tree.configure(yscrollcommand=bill_scroll.set)
bills_tree.pack(side="left", fill="both", expand=True)
bill_scroll.pack(side="right", fill="y")
bills_tree.tag_configure("paid", background="#dff5e1")
bills_tree.tag_configure("unpaid", background="#ffe6e6")
bills_tree.tag_configure("due_soon", background="#fff3cd")   # yellow
bills_tree.tag_configure("overdue", background="#f8d7da")    # red
bills_tree.bind("<<TreeviewSelect>>", update_payment_button_state)

# Payment Buttons
pay_box = tk.Frame(billing_page)
pay_box.pack(fill="x", padx=10, pady=5)
payment_method_var = tk.StringVar(value="Cash")
tk.Label(pay_box, text="Method:").pack(side="left", padx=5)
tk.OptionMenu(pay_box, payment_method_var, "Cash","UPI","Bank Transfer","Cheque").pack(side="left", padx=5)
btn_mark_paid = tk.Button(pay_box, text="Mark Paid", bg="#2ecc71", fg="white", command=mark_selected_bill_paid)
btn_mark_paid.pack(side="left", padx=5)
btn_edit_bill = tk.Button(pay_box, text="Edit Bill", bg="#FF9800", fg="white", command=edit_selected_bill)
btn_edit_bill.pack(side="left", padx=5)
btn_whatsapp = tk.Button(pay_box, text="Send WhatsApp Reminder", bg="#25D366", fg="white", command=send_whatsapp_reminder)
btn_whatsapp.pack(side="left", padx=5)
btn_pdf = tk.Button(
    pay_box,
    text="Generate PDF",
    bg="#6f42c1",
    fg="white",
    command=generate_selected_bill_pdf
)
btn_pdf.pack(side="left", padx=5)
btn_mark_paid.configure(state="disabled")
btn_edit_bill.configure(state="disabled")
btn_whatsapp.configure(state="disabled")

# =========================
# Accounting Page
# =========================

# =========================
# EXPENSE FORM
# =========================
expense_form = tk.LabelFrame(accounting_inner, text="Add Expense")
expense_form.pack(fill="x", padx=10, pady=10)


def add_expense_ui():
    global selected_expense_id_for_edit

    category = entry_exp_category.get()
    desc = entry_exp_desc.get()
    amount = entry_exp_amount.get()
    method = exp_method_var.get()
    date = entry_exp_date.get()

    if not category or not amount:
        messagebox.showerror("Error", "Category & Amount required")
        return

    try:
        amount = float(amount)
    except:
        messagebox.showerror("Error", "Invalid amount")
        return

    # =========================
    # UPDATE MODE
    # =========================
    if selected_expense_id_for_edit:
        from accounting import update_expense
        update_expense(selected_expense_id_for_edit, category, desc, amount, method, date)
        messagebox.showinfo("Success", "Expense updated")
        selected_expense_id_for_edit = None
        btn_save_expense.config(text="Add Expense", bg="#e74c3c")
    # =========================
    # ADD MODE
    # =========================
    else:
        add_expense(category, desc, amount, method, date)
        messagebox.showinfo("Success", "Expense added")

    # Refresh UI
    load_expenses_table()
    refresh_profit()
    refresh_monthly_summary()

    # Clear fields
    entry_exp_category.delete(0, tk.END)
    entry_exp_desc.delete(0, tk.END)
    entry_exp_amount.delete(0, tk.END)
    entry_exp_date.set_date(datetime.now().date())

# =========================
# CLEAR EXPENSE FORM
# =========================
def clear_expense_form():
    global selected_expense_id_for_edit

    selected_expense_id_for_edit = None

    entry_exp_category.delete(0, tk.END)
    entry_exp_desc.delete(0, tk.END)
    entry_exp_amount.delete(0, tk.END)

    # Reset date to today
    entry_exp_date.set_date(datetime.now().date())

    # Reset button
    btn_save_expense.config(text="Add Expense", bg="#e74c3c")

# =========================
# DELETE EXPENSE
# =========================
def delete_selected_expense():
    global selected_expense_id_for_edit

    selected = expenses_tree.selection()

    if not selected:
        messagebox.showerror("Error", "Select an expense")
        return

    exp_id = expenses_tree.item(selected[0], "values")[0]

    confirm = messagebox.askyesno(
        "Confirm Delete",
        "Are you sure you want to delete this expense?"
    )

    if confirm:
        from accounting import delete_expense
        delete_expense(exp_id)

        selected_expense_id_for_edit = None
        load_expenses_table()
        refresh_profit()
        refresh_monthly_summary()
        clear_expense_form()

        messagebox.showinfo("Success", "Expense deleted")


entry_exp_category = add_labeled_entry(expense_form, "Category")
entry_exp_desc = add_labeled_entry(expense_form, "Description")
entry_exp_amount = add_labeled_entry(expense_form, "Amount")
row = tk.Frame(expense_form)
row.pack(fill="x", pady=2)
tk.Label(row, text="Date", width=15, anchor="w").pack(side="left")

entry_exp_date = DateEntry(
    row,
    width=12,
    background="darkgreen",
    foreground="white",
    borderwidth=2,
    date_pattern="yyyy-mm-dd"
)
entry_exp_date.pack(side="left", fill="x", expand=True)

exp_method_var = tk.StringVar(value="Cash")
tk.OptionMenu(expense_form, exp_method_var, "Cash", "UPI", "Bank Transfer").pack(pady=5)

btn_save_expense = tk.Button(
    expense_form,
    text="Add Expense",
    bg="#e74c3c",
    fg="white",
    width=38,
    command=add_expense_ui
)
btn_save_expense.pack(pady=5)

# =========================
# BUTTON FRAME (Side by side)
# =========================
expense_btn_frame = tk.Frame(expense_form)
expense_btn_frame.pack(pady=5)

# Clear button
tk.Button(
    expense_btn_frame,
    text="Clear Form",
    bg="#7f8c8d",
    fg="white",
    width=18,
    command=clear_expense_form
).grid(row=0, column=0, padx=5)

# Delete button
tk.Button(
    expense_btn_frame,
    text="Delete Selected",
    bg="#c0392b",
    fg="white",
    width=18,
    command=delete_selected_expense
).grid(row=0, column=1, padx=5)


# =========================
# PROFIT DASHBOARD
# =========================
profit_frame = tk.LabelFrame(accounting_inner, text="Today's Profit")
profit_frame.pack(fill="x", padx=10, pady=10)

income_var = tk.DoubleVar()
expense_var = tk.DoubleVar()
profit_var = tk.DoubleVar()
monthly_income_var = tk.DoubleVar()
monthly_expense_var = tk.DoubleVar()
monthly_profit_var = tk.DoubleVar()

def refresh_profit():
    income, expense, profit = get_today_profit()
    income_var.set(income)
    expense_var.set(expense)
    profit_var.set(profit)
def refresh_monthly_summary():
    income, expense, profit = get_current_month_summary()
    monthly_income_var.set(income)
    monthly_expense_var.set(expense)
    monthly_profit_var.set(profit)

# =========================
# 💳 PAYMENT ANALYTICS
# =========================
def refresh_payment_analytics():
    from accounting import get_payment_method_report

    data = get_payment_method_report()

    # Clear old chart
    for widget in payment_canvas_frame.winfo_children():
        widget.destroy()

    if not data:
        tk.Label(payment_canvas_frame, text="No payment data").pack()
        return

    methods = [d[0] for d in data]
    amounts = [d[1] for d in data]

    total = sum(amounts)
    payment_total_var.set(total)

    summary_frame = tk.Frame(payment_canvas_frame)
    summary_frame.pack(fill="x", pady=5)

    for i, (method, amount) in enumerate(data):
        var = tk.DoubleVar(value=amount)
        payment_method_vars[method] = var

        card = tk.Frame(summary_frame, bg="#34495e", padx=15, pady=10)
        card.grid(row=0, column=i, padx=10)

        tk.Label(card, text=method, fg="white", bg="#34495e",
                 font=("Arial", 10, "bold")).pack()
        tk.Label(card, text=f"₹ {amount:.2f}", fg="white",
                 bg="#34495e", font=("Arial", 14, "bold")).pack()

    fig, ax = plt.subplots(figsize=(6,5))
    ax.pie(amounts, labels=methods, autopct="%1.1f%%")
    ax.set_title("Payment Distribution")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=payment_canvas_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(pady=10)

    plt.close(fig)

profit_frame.columnconfigure(0, weight=1)
profit_frame.columnconfigure(1, weight=1)
profit_frame.columnconfigure(2, weight=1)

p1 = create_card(profit_frame, "Today Income", income_var, "#2ecc71")
p2 = create_card(profit_frame, "Today Expense", expense_var, "#e74c3c")
p3 = create_card(profit_frame, "Profit", profit_var, "#3498db")

p1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
p2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
p3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

tk.Button(
    profit_frame,
    text="Refresh",
    command=refresh_profit
).grid(row=1, column=0, columnspan=3, pady=5)

tk.Button(
    profit_frame,
    text="📊 Monthly Profit",
    bg="#34495e",
    fg="white",
    command=show_monthly_profit_graph
).grid(row=2, column=0, columnspan=3, pady=5)

tk.Button(
    profit_frame,
    text="📊 Expense Categories",
    bg="#8e44ad",
    fg="white",
    command=show_expense_category_chart
).grid(row=3, column=0, columnspan=3, pady=5)

# =========================
# MONTHLY DASHBOARD
# =========================
monthly_frame = tk.LabelFrame(accounting_inner, text="This Month Summary")
monthly_frame.pack(fill="x", padx=10, pady=10)

monthly_frame.columnconfigure(0, weight=1)
monthly_frame.columnconfigure(1, weight=1)
monthly_frame.columnconfigure(2, weight=1)

m1 = create_card(monthly_frame, "Monthly Income", monthly_income_var, "#27ae60")
m2 = create_card(monthly_frame, "Monthly Expense", monthly_expense_var, "#c0392b")
m3 = create_card(monthly_frame, "Net Profit", monthly_profit_var, "#2980b9")

m1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
m2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
m3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

tk.Button(
    monthly_frame,
    text="Refresh Monthly",
    command=refresh_monthly_summary
).grid(row=4, column=0, columnspan=3, pady=5)

# =========================
# EXPORT REPORTS
# =========================
export_frame = tk.LabelFrame(accounting_inner, text="Export Reports")
export_frame.pack(fill="x", padx=10, pady=10)

tk.Button(
    export_frame,
    text="Export Transactions",
    bg="#16a085",
    fg="white",
    width=25,
    command=export_transactions_to_excel
).pack(pady=5)

tk.Button(
    export_frame,
    text="Export Monthly Financial Report",
    bg="#2980b9",
    fg="white",
    width=25,
    command=export_monthly_report
).pack(pady=5)

# =========================
# PAYMENT METHOD ANALYTICS UI
# =========================
payment_frame = tk.LabelFrame(accounting_inner, text="Payment Method Analytics")
payment_frame.pack(fill="both", expand=True, padx=10, pady=10)

payment_canvas_frame = tk.Frame(payment_frame)
payment_canvas_frame.pack(fill="both", expand=True)

payment_total_var = tk.DoubleVar()
payment_method_vars = {}

# =========================
# EXPENSE TABLE
# =========================
expenses_frame = tk.LabelFrame(accounting_inner, text="Expense Records")
expenses_frame.pack(fill="both", expand=True, padx=10, pady=10)

expenses_tree = ttk.Treeview(
    expenses_frame,
    columns=("id", "category", "description", "amount", "method", "date"),
    show="headings"
)

for col, w in [
    ("id", 50),
    ("category", 140),
    ("description", 220),
    ("amount", 100),
    ("method", 120),
    ("date", 120)
]:
    expenses_tree.heading(col, text=col.title())
    expenses_tree.column(col, width=w)

scroll = ttk.Scrollbar(expenses_frame, orient="vertical", command=expenses_tree.yview)
expenses_tree.configure(yscrollcommand=scroll.set)

expenses_tree.pack(side="left", fill="both", expand=True)
expenses_tree.bind("<<TreeviewSelect>>", on_expense_select)
scroll.pack(side="right", fill="y")

def load_expenses_table():
    for row in expenses_tree.get_children():
        expenses_tree.delete(row)

    expenses = get_all_expenses()

    for e in expenses:
        expenses_tree.insert("", "end", values=e)



# =========================
# Init
# =========================
switch_page("Dashboard")
refresh_metrics()
load_customers_table()
load_customer_dropdown()
load_bills_table()
load_expenses_table()
refresh_profit()
refresh_monthly_summary()
refresh_payment_analytics()
refresh_dashboard_chart()
refresh_customer_status_chart()
draw_arpu_chart()
refresh_revenue_expense_chart()

root.mainloop()

