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
def get_categories():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, categorie FROM categorii ORDER BY categorie")
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_products():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Return product id, name and category name (if available)
    cursor.execute("""
        SELECT p.id, p.name, c.categorie
        FROM products p
        LEFT JOIN categorii c ON p.category_id = c.id
        ORDER BY p.name
    """)
    products = cursor.fetchall()
    conn.close()
    return products

def get_product_by_name(name):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE UPPER(name) = UPPER(?)", (name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def add_product(name, category_id):
    """Ensure a product exists with given name and category_id. Return product id."""
    existing_id = get_product_by_name(name)
    if existing_id:
        return existing_id

    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, category_id) VALUES (?, ?)", (name, category_id))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

# --- Funcții magazine ---
def get_stores():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM stores ORDER BY name")
    stores = cursor.fetchall()
    conn.close()
    return stores

def store_exists(name):
    """Check if a store with this name already exists (case insensitive)."""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM stores WHERE UPPER(name) = UPPER(?)", (name,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def add_store(name):
    """Add a new store if it doesn't already exist.
    Returns: (bool, str) - (success, message)"""
    if store_exists(name):
        return False, f"Magazinul '{name.upper()}' există deja!"
    
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Convert to upper case before saving
    name = name.upper()
    cursor.execute("INSERT INTO stores (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return True, f"Magazinul '{name}' a fost adăugat cu succes!"

def update_store_name(store_id, new_name):
    """Update a store's name."""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Convert to upper case before saving
    new_name = new_name.upper()
    cursor.execute("UPDATE stores SET name = ? WHERE id = ?", (new_name, store_id))
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
    return render_template('index.html', products=products, stores=stores)

@app.route('/add_product', methods=['POST'])
def add_product_route():
    name = request.form['name'].strip()
    category_id = int(request.form['category_id'])
    add_product(name, category_id)
    return redirect('/record_expense')

@app.route('/add_store', methods=['POST'])
def add_store_route():
    name = request.form['name'].strip()
    success, message = add_store(name)
    return render_template('add_store.html', 
                         stores=get_stores(),
                         message=message,
                         success=success)


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

@app.route('/stores/update', methods=['POST'])
def update_store_route():
    store_id = int(request.form['store_id'])
    new_name = request.form['name'].strip()
    if new_name:  # Ensure name is not empty
        update_store_name(store_id, new_name)
    return redirect('/stores/new')

@app.route('/stores/new')
def new_store_page():
    stores = get_stores()
    return render_template('add_store.html', stores=stores)


@app.route('/record_expense')
def record_expense():
    products = get_products()
    stores = get_stores()
    categories = get_categories()
    return render_template('record_expense.html', products=products, stores=stores, categories=categories)

@app.route('/add_expense', methods=['POST'])
def add_expense_route():
    # Allow either selecting an existing product (product_id) or providing a new product_name + category_id
    prod_id_raw = request.form.get('product_id')
    product_id = None
    if prod_id_raw:
        try:
            product_id = int(prod_id_raw)
        except ValueError:
            product_id = None

    if not product_id:
        # create/find product by name
        product_name = request.form.get('product_name', '').strip()
        category_id = request.form.get('category_id')
        if not product_name:
            # nothing provided
            return redirect('/record_expense')
        if category_id:
            try:
                category_id = int(category_id)
            except ValueError:
                category_id = None
        # fallback category_id to None is acceptable; add_product expects an int or None
        product_id = add_product(product_name, category_id)

    store_id = int(request.form['store_id'])
    price = float(request.form['price'])
    quantity = float(request.form['quantity'])
    date_value = request.form['date']
    add_expense(product_id, store_id, price, quantity, date_value)
    # After adding an expense show the expenses page
    return redirect('/cheltuieli')


@app.route('/cheltuieli')
def cheltuieli():
    """Page that lists all expenses."""
    expenses = get_expenses()
    return render_template('cheltuieli.html', expenses=expenses)

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
