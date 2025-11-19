#!/usr/bin/env python3
"""
Migration 0004: Make receipts primary key be nr_bon (TEXT) and populate expenses.receipt_nr.

This script will:
 - create a backup of expenses.db
 - create a new receipts table `receipts_new` with nr_bon TEXT PRIMARY KEY
 - copy existing receipts into receipts_new, generating AUTO-{old_id} for missing nr_bon
 - add `receipt_nr` TEXT column to expenses (if missing) and populate it mapping from old receipt id -> nr_bon
 - leave old receipts table as receipts_old for manual verification

Run: python scripts/migrate_0004_receipts_nrbon.py
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'expenses.db')

if not os.path.exists(DB):
    print('No expenses.db found at', DB)
    sys.exit(1)

bak = DB + '.bak_mig0004'
print('Creating backup:', bak)
shutil.copy2(DB, bak)

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('Creating receipts_new table (nr_bon TEXT PRIMARY KEY)...')
cur.execute('''
CREATE TABLE IF NOT EXISTS receipts_new (
    nr_bon TEXT PRIMARY KEY,
    store_id INTEGER,
    date TEXT
)
''')

print('Copying existing receipts into receipts_new (generating fallback nr_bon for missing values)...')
cur.execute('SELECT id, nr_bon, store_id, date FROM receipts')
rows = cur.fetchall()
id_to_nr = {}
for r in rows:
    old_id, nr_bon, store_id, date = r
    if nr_bon is None or str(nr_bon).strip() == '':
        gen = f'AUTO-{old_id}'
        nr = gen
    else:
        nr = str(nr_bon)
    # ensure uniqueness by appending timestamp if collision
    try:
        cur.execute('INSERT INTO receipts_new (nr_bon, store_id, date) VALUES (?, ?, ?)', (nr, store_id, date))
    except Exception:
        nr = f'{nr}-{int(datetime.utcnow().timestamp())}'
        cur.execute('INSERT INTO receipts_new (nr_bon, store_id, date) VALUES (?, ?, ?)', (nr, store_id, date))
    id_to_nr[old_id] = nr

print('Adding receipt_nr column to expenses (if missing)')
cur.execute("PRAGMA table_info(expenses)")
cols = [c[1] for c in cur.fetchall()]
if 'receipt_nr' not in cols:
    cur.execute('ALTER TABLE expenses ADD COLUMN receipt_nr TEXT')

print('Populating expenses.receipt_nr for rows with receipt_id...')
cur.execute('SELECT id, receipt_id FROM expenses WHERE receipt_id IS NOT NULL')
rows = cur.fetchall()
for eid, old_rid in rows:
    nr = id_to_nr.get(old_rid)
    if nr:
        cur.execute('UPDATE expenses SET receipt_nr = ? WHERE id = ?', (nr, eid))

print('Renaming old receipts table to receipts_old and replacing receipts with receipts_new')
cur.execute('ALTER TABLE receipts RENAME TO receipts_old')
cur.execute('ALTER TABLE receipts_new RENAME TO receipts')

conn.commit()
conn.close()

print('Migration 0004 applied. Backup at', bak)
print('Notes: receipts_old contains original receipts; receipts now use nr_bon as primary key. expenses.receipt_nr populated where possible.')
