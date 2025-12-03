#!/usr/bin/env python3
"""
Migration 0005: Add store types and separate quantity unit columns (buc vs kg)

Changes:
1. Create store_types lookup table and populate defaults
2. Add store_type_id column to stores
3. Add quantity_buc (INTEGER) and quantity_kg (REAL) to expenses
4. Generate a migration report for manual reconciliation

Features:
- --dry-run: show what will be changed without applying
- --force: override running app guard
- Creates a dated backup before applying changes
"""

import sys
import os
import sqlite3
import argparse
import csv
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "expenses.db")
BACKUP_PREFIX = "pre_mig0005"

DEFAULT_STORE_TYPES = [
    ("Pharmacy", "farmacii"),
    ("Supermarket", "supermarket"),
    ("Restaurant", "restaurant"),
    ("Gas Station", "benzinarie"),
]


def check_running_app(force=False):
    """Check if Flask app is running on port 5000. Return True if running (and not forced)."""
    if force:
        return False
    
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('flask' in str(arg).lower() or 'app_web' in str(arg) for arg in cmdline):
                    print(f"[WARN] Flask app appears to be running (PID {proc.info['pid']})")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                pass
    except ImportError:
        pass
    
    # Fallback: try connecting to port 5000
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', 5000))
        s.close()
        if result == 0:
            print("[WARN] Port 5000 appears to be open (Flask app may be running)")
            return True
    except Exception:
        pass
    
    return False


def backup_before_migration():
    """Create a dated backup before applying migration using subprocess."""
    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), "backup_db.py")
    try:
        result = subprocess.run(
            [sys.executable, script_path, "--prefix", BACKUP_PREFIX],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"[ERROR] Backup failed: {result.stderr}")
            sys.exit(1)
        # Extract backup path from output
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            if "Backup created:" in line:
                backup_path = line.split("Backup created:")[-1].strip()
                print(f"[OK] Backup created at: {backup_path}")
                return backup_path
        print("[WARN] Backup output unclear")
        return None
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}")
        sys.exit(1)


def migrate_database(dry_run=False):
    """Apply migration changes."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()
    
    try:
        # Step 1: Create store_types table
        print("\n[1] Creating store_types table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_types (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                code TEXT NOT NULL UNIQUE
            )
        """)
        conn.commit()
        
        # Insert defaults if empty
        cursor.execute("SELECT COUNT(*) FROM store_types")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO store_types (name, code) VALUES (?, ?)",
                DEFAULT_STORE_TYPES
            )
            conn.commit()
            print(f"    Inserted {len(DEFAULT_STORE_TYPES)} default store types")
        else:
            print(f"    store_types already populated")
        
        # Step 2: Add store_type_id to stores if missing
        print("\n[2] Adding store_type_id column to stores...")
        cursor.execute("PRAGMA table_info(stores)")
        cols = {row[1] for row in cursor.fetchall()}
        
        if 'store_type_id' not in cols:
            cursor.execute("ALTER TABLE stores ADD COLUMN store_type_id INTEGER")
            conn.commit()
            print("    Added store_type_id column to stores")
        else:
            print("    store_type_id already exists in stores")
        
        # Step 3: Add quantity_type to expenses if missing
        print("\n[3] Adding quantity_type column to expenses...")
        cursor.execute("PRAGMA table_info(expenses)")
        cols = {row[1] for row in cursor.fetchall()}
        
        if 'quantity_type' not in cols:
            cursor.execute("ALTER TABLE expenses ADD COLUMN quantity_type TEXT DEFAULT 'buc'")
            conn.commit()
            print("    Added quantity_type column to expenses (default: 'buc')")
        else:
            print("    quantity_type already exists in expenses")
        
        # Step 4: Generate migration report for rows with quantity > 0
        print("\n[4] Generating migration report...")
        cursor.execute("""
            SELECT e.id, p.name, e.quantity, s.name, e.date
            FROM expenses e
            JOIN products p ON e.product_id = p.id
            JOIN stores s ON e.store_id = s.id
            WHERE e.quantity > 0 AND (e.quantity_type IS NULL OR e.quantity_type = '')
            ORDER BY e.date DESC
        """)
        
        report_rows = cursor.fetchall()
        
        if report_rows:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                f"migration_report_pre_mig0005_{timestamp}.csv"
            )
            
            with open(report_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Product', 'Legacy Quantity', 'Store', 'Date', 'Action Required'])
                for row in report_rows:
                    writer.writerow(list(row) + ['Manually specify buc or kg'])
            
            print(f"    Migration report created: {report_path}")
            print(f"    {len(report_rows)} rows require manual reconciliation")
        else:
            print("    No rows requiring reconciliation")
        
        if dry_run:
            print("\n[DRY-RUN] Rolling back changes...")
            conn.rollback()
            print("[OK] Dry-run complete. No changes applied.")
        else:
            conn.commit()
            print("\n[OK] Migration 0005 applied successfully")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Migration 0005: Store types and quantity units"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what will be changed without applying"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override running app guard"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Migration 0005: Store Types and Quantity Units")
    print("=" * 60)
    
    # Check for running app
    if check_running_app(force=args.force):
        print("\n[WARN] Flask app is running. It's recommended to stop it before migrating.")
        if not args.force:
            print("       Use --force to override this check.")
            sys.exit(1)
    
    # Create backup
    print("\n[BACKUP] Creating backup before migration...")
    backup_before_migration()
    
    # Run migration
    migrate_database(dry_run=args.dry_run)
    
    print("\n" + "=" * 60)
    if args.dry_run:
        print("Dry-run complete. Review the report and run again without --dry-run")
    else:
        print("Migration complete. Review the migration report for manual steps.")
    print("=" * 60)


if __name__ == "__main__":
    main()
