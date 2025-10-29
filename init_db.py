import sqlite3

# --- Creare baza de date unică pentru toate tabelele ---
conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()

# Creare tabel pentru produse
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    category TEXT
)
''')

# Creare tabel pentru magazine
cursor.execute('''
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
''')

# Creare tabel pentru cheltuieli
cursor.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    store_id INTEGER,
    price REAL,
    quantity REAL,
    date TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(store_id) REFERENCES stores(id)
)
''')

conn.commit()
conn.close()

print("Baza de date a fost creată cu succes!")
