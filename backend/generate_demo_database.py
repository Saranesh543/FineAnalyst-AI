import sqlite3
import random
import os
from datetime import datetime, timedelta
try:
    from faker import Faker
except ImportError:
    print("Please install Faker: pip install faker")
    exit(1)

DB_NAME = "fineanalyst.db"
SEED = 42

def create_schema(cursor):
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Regions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL
        )
    """)
    
    # 2. Categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    """)
    
    # 3. Suppliers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_name TEXT,
            country TEXT
        )
    """)
    
    # 4. Employees
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            title TEXT,
            hire_date DATE
        )
    """)
    
    # 5. Products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            supplier_id INTEGER,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id)")
    
    # 6. Customers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            segment TEXT,
            region_id INTEGER,
            registration_date DATE,
            FOREIGN KEY(region_id) REFERENCES regions(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_region ON customers(region_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(segment)")
    
    # 7. Orders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            employee_id INTEGER,
            order_date DATE NOT NULL,
            status TEXT NOT NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_employee ON orders(employee_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)")
    
    # 8. Order Items
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id)")

def generate_data(cursor):
    fake = Faker()
    Faker.seed(SEED)
    random.seed(SEED)
    
    print("Generating data. This might take a moment...")
    
    # Regions (25)
    print("Generating Regions...")
    regions_data = []
    for _ in range(25):
        regions_data.append((fake.state(), fake.country()))
    cursor.executemany("INSERT INTO regions (name, country) VALUES (?, ?)", regions_data)
    
    # Categories (15)
    print("Generating Categories...")
    category_names = [
        "Electronics", "Clothing", "Home & Garden", "Sports", "Toys", 
        "Books", "Automotive", "Health & Beauty", "Grocery", "Pet Supplies",
        "Jewelry", "Furniture", "Office Products", "Music", "Software"
    ]
    categories_data = [(name, fake.catch_phrase()) for name in category_names]
    cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", categories_data)
    
    # Suppliers (40)
    print("Generating Suppliers...")
    suppliers_data = [(fake.company(), fake.name(), fake.country()) for _ in range(40)]
    cursor.executemany("INSERT INTO suppliers (name, contact_name, country) VALUES (?, ?, ?)", suppliers_data)
    
    # Employees (50)
    print("Generating Employees...")
    job_titles = ["Sales Rep", "Account Manager", "Regional Director", "Sales Associate"]
    employees_data = []
    for _ in range(50):
        hire_date = fake.date_between(start_date='-10y', end_date='today')
        employees_data.append((fake.first_name(), fake.last_name(), random.choice(job_titles), hire_date))
    cursor.executemany("INSERT INTO employees (first_name, last_name, title, hire_date) VALUES (?, ?, ?, ?)", employees_data)
    
    # Products (500)
    print("Generating Products...")
    products_data = []
    product_prices = []
    for _ in range(500):
        cost = round(random.uniform(5.0, 500.0), 2)
        margin = random.uniform(1.2, 2.5)
        price = round(cost * margin, 2)
        product_prices.append(price)
        products_data.append((
            fake.ecommerce_name() if hasattr(fake, 'ecommerce_name') else fake.catch_phrase(),
            random.randint(1, 15), # category_id
            random.randint(1, 40), # supplier_id
            price,
            cost
        ))
    cursor.executemany("INSERT INTO products (name, category_id, supplier_id, price, cost) VALUES (?, ?, ?, ?, ?)", products_data)
    
    # Customers (10,000)
    print("Generating Customers...")
    segments = ["Consumer", "Corporate", "Home Office", "Enterprise"]
    customers_data = []
    for _ in range(10000):
        reg_date = fake.date_between(start_date='-5y', end_date='today')
        customers_data.append((
            fake.first_name(),
            fake.last_name(),
            fake.email(),
            random.choice(segments),
            random.randint(1, 25), # region_id
            reg_date
        ))
    cursor.executemany("INSERT INTO customers (first_name, last_name, email, segment, region_id, registration_date) VALUES (?, ?, ?, ?, ?, ?)", customers_data)
    
    # Orders (50,000) & Order Items
    print("Generating Orders and Order Items...")
    statuses = ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"]
    status_weights = [0.70, 0.15, 0.05, 0.05, 0.05]
    
    # We will build order_items along with orders
    order_items_data = []
    
    # For fast inserts, let's batch manually
    batch_size = 5000
    order_id = 1
    
    for start in range(0, 50000, batch_size):
        orders_batch = []
        items_batch = []
        for _ in range(batch_size):
            customer_id = random.randint(1, 10000)
            employee_id = random.randint(1, 50)
            order_date = fake.date_between(start_date='-3y', end_date='today')
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            # Generate items
            num_items = random.randint(1, 5)
            order_total = 0.0
            
            for _ in range(num_items):
                product_id = random.randint(1, 500)
                qty = random.randint(1, 10)
                unit_price = product_prices[product_id - 1]
                subtotal = round(qty * unit_price, 2)
                order_total += subtotal
                
                items_batch.append((order_id, product_id, qty, unit_price, subtotal))
            
            orders_batch.append((customer_id, employee_id, order_date, status, round(order_total, 2)))
            order_id += 1
            
        cursor.executemany("INSERT INTO orders (customer_id, employee_id, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?)", orders_batch)
        cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)", items_batch)

def validate_database(cursor):
    print("\n--- Database Validation ---")
    
    tables = [
        "regions", "categories", "suppliers", "employees", 
        "products", "customers", "orders", "order_items"
    ]
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Table '{table}': {count:,} rows")
        
    print("\nVerifying Foreign Keys...")
    cursor.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()
    
    if violations:
        print(f"FAILED: Found {len(violations)} foreign key violations!")
        for v in violations:
            print(v)
    else:
        print("SUCCESS: No foreign key violations found.")

def main():
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"Removed existing {DB_NAME}")
        except PermissionError:
            print(f"Warning: Could not remove {DB_NAME} because it is in use by another process (e.g. uvicorn).")
            print("Please stop the backend server, run this script, and then restart the server.")
            exit(1)
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        create_schema(cursor)
        generate_data(cursor)
        conn.commit()
        
        validate_database(cursor)
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()
        
    print(f"\nDatabase generated successfully at {os.path.abspath(DB_NAME)}")

if __name__ == "__main__":
    main()
