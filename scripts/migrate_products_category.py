#!/usr/bin/env python3
"""
migrate_products_category.py

Safely migrate `products` to reference `categorii(id)` via `category_id`.
Usage:
    python scripts/migrate_products_category.py [--create-missing-categories]

The script will:
 - create a backup copy of expenses.db (expenses.db.bak)
 - create products_new with desired schema
 - map textual product.category values to categorii.id (case-insensitive)
 - optionally create missing categorii entries when mapping fails
 - copy rows into products_new preserving IDs
 - rename tables (products -> products_old, products_new -> products)

Review MIGRATION_PLAN.md before running.
"""

import argparse
import shutil
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'expenses.db')
BACKUP_PATH = DB_PATH + '.bak'


def backup_db():
    print(f"Creating backup: {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)


def table_exists(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def migrate(create_missing_categories=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not table_exists(conn, 'products'):
        print('No `products` table found; aborting.')
        conn.close()
        return

    # Create products_new with desired schema
    print('Creating `products_new` table...')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products_new (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category_id INTEGER REFERENCES categorii(id)
        )
    ''')
    conn.commit()

    # Read rows from old products
    cur.execute("PRAGMA table_info(products)")
    cols = [r[1] for r in cur.fetchall()]
    print('Existing products columns:', cols)

    # Determine if old table has textual `category` column
    has_category_text = 'category' in cols
    has_category_id = 'category_id' in cols

    # Fetch all products
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    # Get column order for products
    cur.execute("PRAGMA table_info(products)")
    prod_info = cur.fetchall()
    prod_col_names = [r[1] for r in prod_info]

    print(f'Found {len(products)} products; category_text={has_category_text}, category_id_col={has_category_id}')

    inserted = 0
    created_categories = 0

    for row in products:
        row_dict = dict(zip(prod_col_names, row))
        prod_id = row_dict.get('id')
        name = row_dict.get('name')
        category_id_val = row_dict.get('category_id') if has_category_id else None
        category_text = row_dict.get('category') if has_category_text else None

        final_category_id = None
        if category_id_val:
            final_category_id = category_id_val
        elif category_text:
            # lookup categorii by case-insensitive match
            cur.execute("SELECT id FROM categorii WHERE UPPER(categorie)=UPPER(?)", (category_text,))
            match = cur.fetchone()
            if match:
                final_category_id = match[0]
            else:
                if create_missing_categories:
                    cur.execute("INSERT INTO categorii (categorie) VALUES (?)", (category_text,))
                    conn.commit()
                    final_category_id = cur.lastrowid
                    created_categories += 1
                else:
                    final_category_id = None

        # Insert into products_new preserving id
        cur.execute(
            "INSERT OR REPLACE INTO products_new (id, name, category_id) VALUES (?, ?, ?)",
            (prod_id, name, final_category_id)
        )
        inserted += 1

    conn.commit()

    print(f'Inserted {inserted} rows into products_new. Created {created_categories} missing categories.')

    # Rename tables
    if table_exists(conn, 'products_old'):
        print('Removing existing products_old table...')
        cur.execute('DROP TABLE products_old')
        conn.commit()

    print('Renaming tables: products -> products_old; products_new -> products')
    cur.execute('ALTER TABLE products RENAME TO products_old')
    cur.execute('ALTER TABLE products_new RENAME TO products')
    conn.commit()

    print('Migration complete. Keep the backup (expenses.db.bak) until you verify the app.')
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate products to use category_id')
    parser.add_argument('--create-missing-categories', action='store_true', help='Create missing categories in categorii when mapping fails')
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f'Database not found at {DB_PATH}; aborting.')
        sys.exit(1)

    backup_db()
    migrate(create_missing_categories=args.create_missing_categories)
