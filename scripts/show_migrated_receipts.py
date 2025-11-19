#!/usr/bin/env python3
"""
Quick helper to list a few rows from the `receipts` table so you can verify migrated receipts.
Usage: python scripts/show_migrated_receipts.py --limit 10
"""
import os
import sqlite3
import argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, 'expenses.db')


def main():
    parser = argparse.ArgumentParser(description='Show some rows from receipts table')
    parser.add_argument('--limit', type=int, default=10, help='Number of rows to show')
    args = parser.parse_args()

    if not os.path.exists(DB):
        print('No expenses.db found at', DB)
        return

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute('SELECT nr_bon, store_id, date FROM receipts ORDER BY rowid LIMIT ?', (args.limit,))
    except sqlite3.OperationalError as e:
        print('Error querying receipts table:', e)
        conn.close()
        return

    rows = cur.fetchall()
    if not rows:
        print('No rows found in receipts table.')
    else:
        print(f'Showing up to {args.limit} receipts:')
        print('-' * 60)
        for r in rows:
            nr_bon, store_id, date = r
            print(f'nr_bon: {nr_bon}    store_id: {store_id}    date: {date}')
    conn.close()


if __name__ == '__main__':
    main()
