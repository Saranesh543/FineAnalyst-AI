import sqlite3
import random
from faker import Faker

fake = Faker()

def migrate():
    conn = sqlite3.connect('fineanalyst.db')
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(customers)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "company_name" not in columns:
        cursor.execute("ALTER TABLE customers ADD COLUMN company_name TEXT")
        print("Added company_name")
        
    if "country" not in columns:
        cursor.execute("ALTER TABLE customers ADD COLUMN country TEXT")
        print("Added country")

    conn.commit()

    # Populate
    cursor.execute("SELECT id FROM customers WHERE company_name IS NULL OR country IS NULL")
    rows = cursor.fetchall()
    
    print(f"Populating {len(rows)} customers...")
    updates = []
    for row in rows:
        updates.append((fake.company(), fake.country(), row[0]))
        
    cursor.executemany("UPDATE customers SET company_name = ?, country = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()
    print("Done")

if __name__ == "__main__":
    migrate()
