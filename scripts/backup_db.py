"""
Simple DB backup helper for the expenses_project.

Usage:
  python scripts/backup_db.py                 # uses repo-relative expenses.db and writes to ../expenses_backups/
  python scripts/backup_db.py --db path/to/expenses.db --outdir ../expenses_backups --prefix mybackup

The script copies the SQLite file using shutil.copy2 and appends a timestamp
`YYYYMMDD_HHMMSS` to the filename so backups are unique and easily sortable.

Backups are placed in a folder sibling to the repo named `expenses_backups` by default.
"""

import argparse
import os
import shutil
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Backup the expenses.db file with a dated filename")
    parser.add_argument('--db', dest='db_path', default=None, help='Path to the SQLite DB file (default: expenses.db in repo root)')
    parser.add_argument('--outdir', dest='outdir', default=None, help='Directory to place backups (default: ../expenses_backups)')
    parser.add_argument('--prefix', dest='prefix', default='expenses', help='Prefix for the backup file name (default: expenses)')
    args = parser.parse_args()

    # derive repo root relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, os.pardir))

    db_path = args.db_path or os.path.join(repo_root, 'expenses.db')
    outdir = args.outdir or os.path.abspath(os.path.join(repo_root, os.pardir, 'expenses_backups'))

    if not os.path.isfile(db_path):
        print(f"ERROR: database file not found: {db_path}")
        return 2

    os.makedirs(outdir, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = f"{args.prefix}_{ts}.db"
    dest_path = os.path.join(outdir, base_name)

    try:
        shutil.copy2(db_path, dest_path)
        print(f"Backup created: {dest_path}")
        return 0
    except Exception as e:
        print(f"ERROR copying file: {e}")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
