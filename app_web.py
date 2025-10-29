from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# --- Funcții produse ---
def get_products():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM products ORDER BY name")
    products = cursor.fetchall()
    conn.close()
    return products

def add_product(name, category):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO products (name, category) VALUES (?, ?)", (name, category))
    conn.commit()
    conn.close()

# --- Funcții magazine ---
def get_stores():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM stores ORDER BY name")
    stores = cursor.fetchall()
    conn.close()
    return stores

def add_store(name):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO stores (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

# --- Funcții cheltuieli ---
def add_expense(product_id, store_id, price, quantity, date_value):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (product_id, store_id, price, quantity, date) VALUES (?, ?, ?, ?, ?)",
        (product_id, store_id, price, quantity, date_value)
    )
    conn.commit()
    conn.close()

def get_expenses():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id, p.name, s.name, e.price, e.quantity, e.date
        FROM expenses e
        LEFT JOIN products p ON e.product_id = p.id
        LEFT JOIN stores s ON e.store_id = s.id
        ORDER BY e.date DESC
    """)
    expenses = cursor.fetchall()
    conn.close()
    return expenses

# --- Rute web ---
@app.route('/')
def index():
    products = get_products()
    stores = get_stores()
    expenses = get_expenses()
    return render_template('index.html', products=products, stores=stores, expenses=expenses)

@app.route('/add_product', methods=['POST'])
def add_product_route():
    name = request.form['name'].strip()
    category = request.form['category'].strip()
    add_product(name, category)
    return redirect('/')

@app.route('/add_store', methods=['POST'])
def add_store_route():
    name = request.form['name'].strip()
    add_store(name)
    return redirect('/')

@app.route('/add_expense', methods=['POST'])
def add_expense_route():
    product_id = int(request.form['product_id'])
    store_id = int(request.form['store_id'])
    price = float(request.form['price'])
    quantity = float(request.form['quantity'])
    date_value = request.form['date']
    add_expense(product_id, store_id, price, quantity, date_value)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
