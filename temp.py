import sqlite3

conn = sqlite3.connect("isp_billing.db")
cursor = conn.cursor()

cursor.execute("SELECT DISTINCT status FROM customers")
print(cursor.fetchall())

conn.close()



