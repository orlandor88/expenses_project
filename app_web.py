from flask import Flask, render_template, request, redirect, make_response, jsonify
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


def ensure_receipts_schema():
    """Ensure receipts table exists and expenses has receipt_id column."""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Create receipts table if missing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY,
            store_id INTEGER,
            nr_bon TEXT,
            date TEXT
        )
    """)
    # Ensure expenses has receipt_id column
    cursor.execute("PRAGMA table_info(expenses)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'receipt_id' not in cols:
        try:
            cursor.execute("ALTER TABLE expenses ADD COLUMN receipt_id INTEGER")
        except Exception:
            # If alter fails, skip (older SQLite versions should support ADD COLUMN)
            pass
    conn.commit()
    conn.close()


def ensure_expense_discount_column():
    """Ensure the expenses table has a discount column (REAL)."""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expenses)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'discount' not in cols:
        try:
            cursor.execute("ALTER TABLE expenses ADD COLUMN discount REAL DEFAULT 0.0")
        except Exception:
            # best-effort; if it fails we'll still proceed
            pass
    conn.commit()
    conn.close()


def create_receipt(store_id, nr_bon, date_value):
    ensure_receipts_schema()
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO receipts (store_id, nr_bon, date) VALUES (?, ?, ?)",
                   (store_id, nr_bon, date_value))
    conn.commit()
    rid = cursor.lastrowid
    conn.close()
    return rid

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
def add_expense(product_id, store_id, price, quantity, date_value, receipt_id=None, discount=0.0):
    # ensure discount column exists (best-effort)
    ensure_expense_discount_column()
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    if receipt_id is not None:
        cursor.execute(
            "INSERT INTO expenses (product_id, store_id, price, quantity, date, receipt_id, discount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, store_id, price, quantity, date_value, receipt_id, discount)
        )
    else:
        cursor.execute(
            "INSERT INTO expenses (product_id, store_id, price, quantity, date, discount) VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, store_id, price, quantity, date_value, discount)
        )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_expenses():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("""
     SELECT e.id, p.name, s.name, e.price, e.quantity, IFNULL(e.discount, 0) as discount,
         (e.price * e.quantity - IFNULL(e.discount,0)) AS total,
         e.date, r.nr_bon, r.id
     FROM expenses e
     LEFT JOIN products p ON e.product_id = p.id
     LEFT JOIN stores s ON e.store_id = s.id
     LEFT JOIN receipts r ON e.receipt_id = r.id
     ORDER BY COALESCE(r.id, 0) DESC, e.date DESC
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


def delete_receipt(receipt_id):
    """Delete a receipt and any related expenses."""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE receipt_id = ?", (receipt_id,))
    cursor.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
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


@app.route('/products/search')
def products_search():
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    if q:
        cursor.execute("""
            SELECT p.id, p.name, c.categorie
            FROM products p
            LEFT JOIN categorii c ON p.category_id = c.id
            WHERE UPPER(p.name) LIKE UPPER(?)
            ORDER BY p.name
            LIMIT 10
        """, (f"%{q}%",))
    else:
        cursor.execute("""
            SELECT p.id, p.name, c.categorie
            FROM products p
            LEFT JOIN categorii c ON p.category_id = c.id
            ORDER BY p.name
            LIMIT 10
        """)
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({'id': r[0], 'name': r[1], 'category': r[2]})
    return jsonify(results)


@app.route('/create_receipt', methods=['POST'])
def create_receipt_route():
    # create a receipt header and return its id
    store_id = request.form.get('store_id')
    nr_bon = request.form.get('nr_bon', '').strip()
    date_value = request.form.get('date')
    if not store_id:
        return jsonify({'success': False, 'error': 'store_id_required'}), 400
    try:
        store_id = int(store_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'invalid_store_id'}), 400
    rid = create_receipt(store_id, nr_bon, date_value)
    return jsonify({'success': True, 'receipt_id': rid})


@app.route('/add_line_item', methods=['POST'])
def add_line_item_route():
    # Add an expense line associated with a receipt (AJAX)
    receipt_id = request.form.get('receipt_id')
    if not receipt_id:
        return jsonify({'success': False, 'error': 'receipt_id_required'}), 400
    try:
        receipt_id = int(receipt_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'invalid_receipt_id'}), 400

    # product may be provided as id or as new product_name + category_id
    prod_id_raw = request.form.get('product_id')
    product_id = None
    if prod_id_raw:
        try:
            product_id = int(prod_id_raw)
        except ValueError:
            product_id = None

    if not product_id:
        product_name = request.form.get('product_name', '').strip()
        category_id = request.form.get('category_id')
        if not product_name:
            return jsonify({'success': False, 'error': 'product_name_required'}), 400
        try:
            category_id = int(category_id) if category_id else None
        except ValueError:
            category_id = None
        product_id = add_product(product_name, category_id)

    price = request.form.get('price')
    qty = request.form.get('quantity')
    discount = request.form.get('discount')
    date_value = request.form.get('date')
    # retrieve store_id from receipts table for this receipt (to populate expense.store_id)
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT store_id, date FROM receipts WHERE id = ?", (receipt_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'success': False, 'error': 'receipt_not_found'}), 400
    store_id = row[0]
    # if date not provided for line, fallback to receipt date or today's date
    if not date_value:
        date_value = row[1]

    try:
        price = float(price)
    except Exception:
        price = 0.0
    try:
        qty = float(qty)
    except Exception:
        qty = 1.0
    try:
        discount = float(discount) if discount not in (None, '') else 0.0
    except Exception:
        discount = 0.0

    expense_id = add_expense(product_id, store_id, price, qty, date_value, receipt_id=receipt_id, discount=discount)

    # return a small representation for UI
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT p.name FROM products p WHERE p.id = ?", (product_id,))
    r = cursor.fetchone()
    pname = r[0] if r else ''
    conn.close()

    return jsonify({'success': True, 'expense_id': expense_id, 'product_name': pname, 'price': price, 'quantity': qty, 'discount': discount})


@app.route('/complete_receipt', methods=['POST'])
def complete_receipt_route():
    # For now, just acknowledge and redirect client to expenses list
    receipt_id = request.form.get('receipt_id')
    if not receipt_id:
        return jsonify({'success': False, 'error': 'receipt_id_required'}), 400
    return jsonify({'success': True, 'redirect': '/cheltuieli'})


@app.route('/delete_receipt', methods=['POST'])
def delete_receipt_route():
    receipt_id = request.form.get('receipt_id')
    if not receipt_id:
        return jsonify({'success': False, 'error': 'receipt_id_required'}), 400
    try:
        rid = int(receipt_id)
    except Exception:
        return jsonify({'success': False, 'error': 'invalid_receipt_id'}), 400
    delete_receipt(rid)
    return jsonify({'success': True})


@app.route('/delete_expense', methods=['POST'])
def delete_expense_route():
    eid = request.form.get('expense_id')
    if not eid:
        return jsonify({'success': False, 'error': 'expense_id_required'}), 400
    try:
        eid = int(eid)
    except Exception:
        return jsonify({'success': False, 'error': 'invalid_expense_id'}), 400
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # fetch row for possible client-side undo
    cursor.execute('SELECT product_id, store_id, price, quantity, date, receipt_id, IFNULL(discount,0) FROM expenses WHERE id = ?', (eid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'not_found'}), 404
    cursor.execute('DELETE FROM expenses WHERE id = ?', (eid,))
    conn.commit()
    conn.close()
    # return deleted row details for undo on client
    return jsonify({'success': True, 'deleted': {'product_id': row[0], 'store_id': row[1], 'price': row[2], 'quantity': row[3], 'date': row[4], 'receipt_id': row[5], 'discount': row[6]}})


@app.route('/update_expense', methods=['POST'])
def update_expense_route():
    eid = request.form.get('expense_id')
    if not eid:
        return jsonify({'success': False, 'error': 'expense_id_required'}), 400
    try:
        eid = int(eid)
    except Exception:
        return jsonify({'success': False, 'error': 'invalid_expense_id'}), 400
    # allowed fields: price, quantity, discount
    price = request.form.get('price')
    quantity = request.form.get('quantity')
    discount = request.form.get('discount')
    updates = []
    params = []
    if price is not None:
        try:
            price_val = float(price)
        except Exception:
            return jsonify({'success': False, 'error': 'invalid_price'}), 400
        updates.append('price = ?')
        params.append(price_val)
    if quantity is not None:
        try:
            qty_val = float(quantity)
        except Exception:
            return jsonify({'success': False, 'error': 'invalid_quantity'}), 400
        updates.append('quantity = ?')
        params.append(qty_val)
    if discount is not None:
        try:
            disc_val = float(discount)
        except Exception:
            return jsonify({'success': False, 'error': 'invalid_discount'}), 400
        updates.append('discount = ?')
        params.append(disc_val)
    if not updates:
        return jsonify({'success': False, 'error': 'no_fields'}), 400
    params.append(eid)
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    sql = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(sql, params)
    conn.commit()
    # fetch updated row to return new totals
    cursor.execute('SELECT price, quantity, IFNULL(discount,0) FROM expenses WHERE id = ?', (eid,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return jsonify({'success': False, 'error': 'not_found_after_update'}), 500
    price, quantity, discount = r
    total = price * quantity - (discount or 0.0)
    return jsonify({'success': True, 'price': price, 'quantity': quantity, 'discount': discount, 'total': total})

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
    # optional discount field
    discount = request.form.get('discount')
    try:
        discount = float(discount) if discount not in (None, '') else 0.0
    except Exception:
        discount = 0.0
    add_expense(product_id, store_id, price, quantity, date_value, discount=discount)
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
