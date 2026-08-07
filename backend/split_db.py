import sqlite3
import shutil
import os

print("Copying fineanalyst.db to analytics.db...")
shutil.copy2("fineanalyst.db", "analytics.db")

auth_tables = ["users", "sessions", "messages"]
analytics_tables = [
    "regions", "categories", "suppliers", "employees", 
    "products", "customers", "orders", "order_items"
]

print("Connecting to analytics.db to drop auth tables...")
with sqlite3.connect("analytics.db") as conn:
    cursor = conn.cursor()
    for table in auth_tables:
        print(f"  Dropping {table} from analytics.db")
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()

print("Connecting to fineanalyst.db to drop analytics tables...")
with sqlite3.connect("fineanalyst.db") as conn:
    cursor = conn.cursor()
    for table in analytics_tables:
        print(f"  Dropping {table} from fineanalyst.db")
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()

print("Database split complete!")
