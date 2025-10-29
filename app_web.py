from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import date
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_DB = os.path.join(BASE_DIR, "products.db")
EXPENSES_DB = os.path.join(BASE_DIR, "expenses.db")

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

# --- Funcții auxiliare ---
def query_db(db_name, query, params=()):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

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

# === Rapoarte ===
@app.route("/reports")
def reports_home():
    return render_template("reports.html")


@app.route("/reports/monthly")
def report_monthly():
    query = """
        SELECT substr(date, 1, 7) AS luna, SUM(price * quantity) AS total
        FROM expenses
        GROUP BY substr(date, 1, 7)
        ORDER BY luna DESC
    """
    data = query_db(EXPENSES_DB, query)
    return render_template("report_monthly.html", data=data)


@app.route("/reports/products")
def report_products():
    query = """
        SELECT p.name, SUM(e.price * e.quantity) AS total
        FROM expenses e
        JOIN products p ON e.product_id = p.id
        GROUP BY p.name
        ORDER BY total DESC
    """
    data = query_db(EXPENSES_DB, query)
    return render_template("report_products.html", data=data)

if __name__ == '__main__':
    app.run(debug=True)
