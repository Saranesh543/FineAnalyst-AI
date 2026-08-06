"""
Database Seeder — Production Bootstrap

Creates the FineAnalyst demo database with realistic data if and only if
the database is empty (no tables present). Safe to run on every startup.

This is designed to be called from main.py lifespan on Render where the
SQLite file is not checked into git.
"""
import logging
import os
import random
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SEED = 42


def _needs_seeding(db_path: str) -> bool:
    """Return True if the database file is missing or has no tables."""
    if not os.path.exists(db_path):
        return True
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True


def seed_database(db_path: str = "fineanalyst.db") -> None:
    """
    Create and populate the FineAnalyst demo database.
    Only runs if the database is empty or missing.
    """
    if not _needs_seeding(db_path):
        logger.info("Database already seeded (%s). Skipping.", db_path)
        return

    logger.info("Database is empty. Seeding demo data into %s ...", db_path)

    try:
        from faker import Faker
    except ImportError:
        logger.error("Faker not installed. Cannot seed database. Add 'faker' to requirements.txt.")
        return

    random.seed(SEED)
    fake = Faker()
    fake.seed_instance(SEED)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_email TEXT,
            phone TEXT,
            country TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            supplier_id INTEGER REFERENCES suppliers(id),
            unit_price REAL,
            stock_quantity INTEGER
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            segment TEXT,
            region_id INTEGER REFERENCES regions(id),
            registration_date DATE,
            company_name TEXT,
            country TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            employee_id INTEGER,
            order_date DATE,
            total_amount REAL,
            status TEXT,
            region_id INTEGER REFERENCES regions(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity INTEGER,
            unit_price REAL,
            subtotal REAL
        );

        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
        CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
        CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
        CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
    """)

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------
    region_names = [
        ("North America", "USA"), ("Europe", "Germany"), ("Asia Pacific", "Japan"),
        ("Latin America", "Brazil"), ("Middle East", "UAE"), ("Africa", "South Africa"),
    ]
    cursor.executemany("INSERT INTO regions (name, country) VALUES (?, ?)", region_names)
    region_ids = [r[0] for r in cursor.execute("SELECT id FROM regions").fetchall()]

    suppliers_data = [(fake.company(), fake.company_email(), fake.phone_number(), fake.country()) for _ in range(15)]
    cursor.executemany("INSERT INTO suppliers (name, contact_email, phone, country) VALUES (?,?,?,?)", suppliers_data)
    supplier_ids = [r[0] for r in cursor.execute("SELECT id FROM suppliers").fetchall()]

    categories = ["Electronics", "Software", "Consulting", "Hardware", "Accessories", "Cloud Services", "Training"]
    products_data = []
    for _ in range(60):
        products_data.append((
            fake.catch_phrase(),
            random.choice(categories),
            random.choice(supplier_ids),
            round(random.uniform(50, 5000), 2),
            random.randint(0, 500),
        ))
    cursor.executemany("INSERT INTO products (name, category, supplier_id, unit_price, stock_quantity) VALUES (?,?,?,?,?)", products_data)
    product_ids = [r[0] for r in cursor.execute("SELECT id FROM products").fetchall()]
    product_prices = {r[0]: r[1] for r in cursor.execute("SELECT id, unit_price FROM products").fetchall()}

    segments = ["Enterprise", "SMB", "Startup", "Government", "Non-profit"]
    customers_data = []
    for _ in range(120):
        customers_data.append((
            fake.first_name(), fake.last_name(), fake.email(),
            random.choice(segments), random.choice(region_ids),
            fake.date_between(start_date="-3y", end_date="-1y").isoformat(),
            fake.company(), fake.country(),
        ))
    cursor.executemany(
        "INSERT INTO customers (first_name, last_name, email, segment, region_id, registration_date, company_name, country) VALUES (?,?,?,?,?,?,?,?)",
        customers_data
    )
    customer_ids = [r[0] for r in cursor.execute("SELECT id FROM customers").fetchall()]

    statuses = ["completed", "completed", "completed", "pending", "cancelled"]
    order_rows = []
    item_rows = []
    base_date = datetime(2023, 1, 1)

    for _ in range(800):
        cust_id = random.choice(customer_ids)
        region_id = random.choice(region_ids)
        order_date = (base_date + timedelta(days=random.randint(0, 730))).date().isoformat()
        status = random.choice(statuses)
        num_items = random.randint(1, 5)
        items = [(random.choice(product_ids), random.randint(1, 10)) for _ in range(num_items)]
        total = sum(product_prices[pid] * qty for pid, qty in items)
        order_rows.append((cust_id, None, order_date, round(total, 2), status, region_id))
        for pid, qty in items:
            up = product_prices[pid]
            item_rows.append((None, pid, qty, up, round(up * qty, 2)))  # order_id filled below

    cursor.executemany(
        "INSERT INTO orders (customer_id, employee_id, order_date, total_amount, status, region_id) VALUES (?,?,?,?,?,?)",
        order_rows
    )
    order_ids = [r[0] for r in cursor.execute("SELECT id FROM orders ORDER BY id").fetchall()]

    filled_items = []
    for oid, (_, pid, qty, up, sub) in zip(order_ids, item_rows):
        filled_items.append((oid, pid, qty, up, sub))
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?,?,?,?,?)",
        filled_items
    )

    conn.commit()
    conn.close()

    logger.info(
        "Database seeded: %d regions, %d suppliers, %d products, %d customers, %d orders, %d order_items",
        len(region_ids), len(supplier_ids), len(product_ids),
        len(customer_ids), len(order_ids), len(filled_items),
    )
