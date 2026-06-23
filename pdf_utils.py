from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import os

def generate_bill_pdf(bill):
    (
        bill_id, customer, month, amount, due,
        status, method, paid_date,
        reminder_count, last_reminder
    ) = bill

    filename = f"BILL_{bill_id}_{month}.pdf"
    filepath = os.path.join("bills", filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "Gaba Broadband")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, "Internet Service Provider")

    # Bill Info
    y = height - 140
    c.setFont("Helvetica", 11)

    c.drawString(50, y, f"Bill ID: {bill_id}")
    c.drawString(300, y, f"Bill Month: {month}")

    y -= 25
    c.drawString(50, y, f"Customer Name: {customer}")
    c.drawString(300, y, f"Status: {status}")

    y -= 25
    c.drawString(50, y, f"Amount: ₹{amount}")
    c.drawString(300, y, f"Due Date: {due}")

    if status == "PAID":
        y -= 25
        c.drawString(50, y, f"Paid Via: {method}")
        c.drawString(300, y, f"Paid On: {paid_date}")

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 80, "This is a system generated bill.")
    c.drawString(50, 65, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    c.showPage()
    c.save()

    return filepath
