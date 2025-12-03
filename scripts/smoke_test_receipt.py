#!/usr/bin/env python3
"""
Simple smoke test for receipts migration and basic DB inserts.
Run after migration to verify receipts and discount columns exist and basic insert works.

Usage: python scripts/smoke_test_receipt.py
"""
import sqlite3
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'expenses.db')

if not os.path.exists(DB):
    print('No expenses.db found at', DB)
    sys.exit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('Checking receipts table...')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='receipts'")
if not cur.fetchone():
    print('receipts table missing')
    sys.exit(1)
else:
    print('receipts table exists')

print('Checking expenses columns...')
cur.execute('PRAGMA table_info(expenses)')
cols = [r[1] for r in cur.fetchall()]
print('expenses columns:', cols)
if 'discount' not in cols or 'receipt_id' not in cols:
    print('Expected columns not present')
    sys.exit(1)

print('Inserting test receipt and line...')
cur.execute('INSERT INTO receipts (store_id, nr_bon, date) VALUES (?, ?, ?)', (1, 'TEST123', '2025-11-19'))
rid = cur.lastrowid
cur.execute('INSERT INTO expenses (product_id, store_id, price, quantity, date, receipt_id, discount) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (1, 1, 10.0, 2, '2025-11-19', rid, 1.5))
conn.commit()

cur.execute('SELECT e.price, e.quantity, e.discount FROM expenses WHERE receipt_id = ?', (rid,))
row = cur.fetchone()
print('Inserted line:', row)
expected_total = row[0]*row[1] - row[2]
print('Computed total:', expected_total)

print('Cleaning up test rows...')
cur.execute('DELETE FROM expenses WHERE receipt_id = ?', (rid,))
cur.execute('DELETE FROM receipts WHERE id = ?', (rid,))
conn.commit()
conn.close()

print('Smoke test OK')
