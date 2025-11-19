#!/usr/bin/env python3
"""
Migration 0003: create receipts table and add receipt_id and discount columns to expenses.
This script makes a backup of expenses.db, then applies the changes if needed.

Usage: python scripts/migrate_0003_receipts.py
"""
import shutil
import sqlite3
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'expenses.db')

if not os.path.exists(DB):
    print('No expenses.db found at', DB)
    sys.exit(1)

bak = DB + '.bak_mig0003'
print('Creating backup:', bak)
shutil.copy2(DB, bak)

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('Creating receipts table if missing...')
cur.execute('''
CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY,
    store_id INTEGER,
    nr_bon TEXT,
    date TEXT
)
''')

print('Checking expenses columns...')
cur.execute("PRAGMA table_info(expenses)")
cols = [r[1] for r in cur.fetchall()]
if 'receipt_id' not in cols:
    print('Adding column receipt_id to expenses')
    cur.execute('ALTER TABLE expenses ADD COLUMN receipt_id INTEGER')
else:
    print('receipt_id already exists')

if 'discount' not in cols:
    print('Adding column discount to expenses')
    cur.execute("ALTER TABLE expenses ADD COLUMN discount REAL DEFAULT 0.0")
else:
    print('discount already exists')

conn.commit()
conn.close()

print('Migration applied. Please verify your app and tests. Backup kept at', bak)
