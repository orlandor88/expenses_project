Migration plan: products -> use category_id from `categorii`

Goal
----
Migrate the existing `products` table to reference `categorii(id)` via a `category_id` foreign key. Preserve existing product names and map textual categories (if any) to the `categorii` table. This plan is small, reversible, and safe for the local SQLite DB.

High-level steps
----------------
1. Backup the DB file.
2. Inspect current `products` schema.
3. Create a new table `products_new` with the desired schema (id, name, category_id).
4. For each row in the old `products` table:
   - If `category_id` already exists and is non-null, keep it.
   - Else, try to find a matching `categorii` row by name (case-insensitive).
   - If found, use that `categorii.id`.
   - If not found, optionally insert a new `categorii` row and use its id (configurable).
   - Insert the product into `products_new` preserving id when possible.
5. Rename tables: move `products` -> `products_old`, `products_new` -> `products`.
6. Verify data and application behavior.
7. Remove `products_old` after a safe verification period.

Files included
--------------
- `scripts/migrate_products_category.py` - a safe Python script that automates the steps above. It creates a DB backup and prints a summary at the end.

Commands (manual)
-----------------
# Backup
cp expenses.db expenses.db.bak

# Run migration script (recommended)
python scripts/migrate_products_category.py --create-missing-categories

# If you prefer to run SQL manually, here are the main statements (example):

-- create new table
CREATE TABLE products_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category_id INTEGER REFERENCES categorii(id)
);

-- example of inserting mapping: (run inside sqlite3 or via Python)
-- this finds a matching categorie row; if none found you may need to create it first
INSERT INTO products_new (id, name, category_id)
SELECT p.id, p.name, c.id
FROM products p
LEFT JOIN categorii c ON UPPER(c.categorie) = UPPER(COALESCE(p.category, ''));

-- rename (run only after verification)
ALTER TABLE products RENAME TO products_old;
ALTER TABLE products_new RENAME TO products;

-- verify, then drop old
DROP TABLE products_old; -- only after manual verification

Rollback
--------
If anything goes wrong, restore the backup:
cp expenses.db.bak expenses.db

Notes
-----
- The script is conservative: it preserves original ids where possible and keeps a backup automatically.
- The script supports an option to create missing categories if a product's textual category has no match in `categorii`.
- SQLite has limited ALTER TABLE support; we use create-copy-rename approach which is reliable.

If you want, I can run the migration script now (it will create a backup first). Otherwise you can review the script and run it yourself.
