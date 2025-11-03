from flask import Flask, render_template, request, redirect, make_response
import sqlite3
import os
import csv
from io import StringIO

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


def delete_store(store_id):
    """Delete a store and any related expenses."""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Remove expenses referencing this store first to keep DB consistent
    cursor.execute("DELETE FROM expenses WHERE store_id = ?", (store_id,))
    cursor.execute("DELETE FROM stores WHERE id = ?", (store_id,))
    conn.commit()
    conn.close()


@app.route('/stores/delete', methods=['POST'])
def delete_store_route():
    store_id = int(request.form['store_id'])
    delete_store(store_id)
    return redirect('/stores/new')


@app.route('/stores/new')
def new_store_page():
    stores = get_stores()
    return render_template('add_store.html', stores=stores)


@app.route('/record_expense')
def record_expense():
    products = get_products()
    stores = get_stores()
    return render_template('record_expense.html', products=products, stores=stores)

@app.route('/add_expense', methods=['POST'])
def add_expense_route():
    product_id = int(request.form['product_id'])
    store_id = int(request.form['store_id'])
    price = float(request.form['price'])
    quantity = float(request.form['quantity'])
    date_value = request.form['date']
    add_expense(product_id, store_id, price, quantity, date_value)
    return redirect('/')

# === Funcții auxiliare pentru rapoarte ===
def get_date_filter_clause(start_date=None, end_date=None):
    """Generate SQL WHERE clause for date filtering"""
    conditions = []
    params = []
    
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)
    
    if conditions:
        return " WHERE " + " AND ".join(conditions), params
    return "", []

def generate_csv(data, headers):
    """Generate CSV file from data"""
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(headers)
    writer.writerows(data)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# === Rapoarte ===
@app.route("/reports")
def reports_home():
    return render_template("reports.html")

@app.route("/reports/monthly")
def report_monthly():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    where_clause, params = get_date_filter_clause(start_date, end_date)
    
    query = f"""
        SELECT substr(date, 1, 7) AS luna, SUM(price * quantity) AS total
        FROM expenses
        {where_clause}
        GROUP BY substr(date, 1, 7)
        ORDER BY luna DESC
    """
    data = query_db(EXPENSES_DB, query, params)
    
    if request.args.get('format') == 'csv':
        headers = ['Luna', 'Total (lei)']
        return generate_csv(data, headers)
        
    return render_template("report_monthly.html", data=data, 
                         start_date=start_date, end_date=end_date)

@app.route("/reports/products")
def report_products():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    where_clause, params = get_date_filter_clause(start_date, end_date)
    
    if where_clause:
        where_clause = where_clause.replace("date", "e.date")
    
    query = f"""
        SELECT p.name, SUM(e.price * e.quantity) AS total
        FROM expenses e
        JOIN products p ON e.product_id = p.id
        {where_clause}
        GROUP BY p.name
        ORDER BY total DESC
    """
    data = query_db(EXPENSES_DB, query, params)
    
    if request.args.get('format') == 'csv':
        headers = ['Produs', 'Total (lei)']
        return generate_csv(data, headers)
        
    return render_template("report_products.html", data=data,
                         start_date=start_date, end_date=end_date)

@app.route("/reports/stores")
def report_stores():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    where_clause, params = get_date_filter_clause(start_date, end_date)
    
    if where_clause:
        where_clause = where_clause.replace("date", "e.date")
    
    query = f"""
        SELECT s.name, 
               COUNT(*) as num_transactions,
               SUM(e.price * e.quantity) AS total
        FROM expenses e
        JOIN stores s ON e.store_id = s.id
        {where_clause}
        GROUP BY s.name
        ORDER BY total DESC
    """
    data = query_db(EXPENSES_DB, query, params)
    
    if request.args.get('format') == 'csv':
        headers = ['Magazin', 'Număr tranzacții', 'Total (lei)']
        return generate_csv(data, headers)
        
    return render_template("report_stores.html", data=data,
                         start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    app.run(debug=True)
