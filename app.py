import sqlite3
from datetime import date

def get_products():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products ORDER BY name")
    products = cursor.fetchall()
    conn.close()
    return products

def add_product(name, category):
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO products (name, category) VALUES (?, ?)", (name, category))
    conn.commit()
    conn.close()

def add_expense(product_id, store, price, quantity):
    # Preluăm numele produsului din products.db
    conn_prod = sqlite3.connect('products.db')
    cursor_prod = conn_prod.cursor()
    cursor_prod.execute("SELECT name FROM products WHERE id = ?", (product_id,))
    result = cursor_prod.fetchone()
    conn_prod.close()

    if result:
        name = result[0]
    else:
        print("Produsul nu a fost găsit în baza de date.")
        return
    # Adăugăm cheltuiala în expenses.db
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (product_id, name, store, price, cantitate, date) VALUES (?, ?, ?, ?, ?, ?)",
                   (product_id, name, store, price, quantity, str(date.today())))
    conn.commit()
    conn.close()

# --- Interfață simplă în consolă ---
while True:
    print("\n=== Adaugă o cheltuială ===")
    products = get_products()
    if not products:
        print("Nu există produse. Adaugă unul nou mai jos.")
    else:
        for p in products:
            print(f"{p[0]}. {p[1]}")

    print("0. Adaugă produs nou")

    choice = int(input("Alege produsul (ID): "))

    if choice == 0:
        name = input("Nume produs: ").strip()
        category = input("Categorie: ").strip()
        add_product(name, category)
        products = get_products()
        print(f"Produsul '{name}' a fost adăugat.")
        continue

    store = input("Magazin: ").strip()
    price = float(input("Preț: "))
    quantity = float(input("Cantitate: "))

    add_expense(choice, store, price, quantity)
    print("Cheltuiala a fost adăugată cu succes!")

    another = input("Vrei să mai adaugi o cheltuială? (da/nu): ").lower()
    if another != 'da':
        break
