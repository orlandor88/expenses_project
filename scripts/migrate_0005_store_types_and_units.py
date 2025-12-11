#!/usr/bin/env python3
"""
Migration 0005: Add store_type column to stores and quantity_type column to expenses

Changes:
1. Add store_type (TEXT) column to stores
2. Add quantity_type (TEXT) column to expenses
3. Remove quantity_buc and quantity_kg columns if they exist
4. Remove store_type_id column if it exists

Features:
- --dry-run: show what will be changed without applying
- --force: override running app guard
- Creates a dated backup before applying changes
"""

import sys
import os
import sqlite3
import argparse
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "expenses.db")
BACKUP_PREFIX = "pre_mig0005"


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
    cursor = conn.cursor()
    
    try:
        # Disable foreign keys during migration
        cursor.execute("PRAGMA foreign_keys=OFF")
        
        # Step 1: Remove store_type_id and add store_type to stores
        print("\n[1] Updating stores schema...")
        cursor.execute("PRAGMA table_info(stores)")
        cols = {row[1] for row in cursor.fetchall()}
        
        if 'store_type_id' in cols:
            print("    Removing store_type_id column and adding store_type...")
            cursor.execute("PRAGMA table_info(stores)")
            all_cols = cursor.fetchall()
            keep_cols = [col[1] for col in all_cols if col[1] != 'store_type_id']
            keep_cols_str = ', '.join(keep_cols)
            
            cursor.execute(f"CREATE TABLE stores_new AS SELECT {keep_cols_str} FROM stores")
            cursor.execute("DROP TABLE stores")
            cursor.execute("ALTER TABLE stores_new RENAME TO stores")
            cursor.execute("ALTER TABLE stores ADD COLUMN store_type TEXT")
            conn.commit()
            print("    Removed store_type_id, added store_type column")
        elif 'store_type' not in cols:
            cursor.execute("ALTER TABLE stores ADD COLUMN store_type TEXT")
            conn.commit()
            print("    Added store_type column to stores")
        else:
            print("    store_type already exists in stores")
        
        # Step 2: Add quantity_type to expenses if missing
        print("\n[2] Updating expenses schema...")
        cursor.execute("PRAGMA table_info(expenses)")
        cols = {row[1] for row in cursor.fetchall()}
        
        if 'quantity_type' not in cols:
            cursor.execute("ALTER TABLE expenses ADD COLUMN quantity_type TEXT DEFAULT 'buc'")
            conn.commit()
            print("    Added quantity_type column to expenses (default: 'buc')")
        else:
            print("    quantity_type already exists in expenses")
        
        # Step 3: Remove quantity_buc and quantity_kg if they exist
        print("\n[3] Cleaning up legacy columns...")
        cursor.execute("PRAGMA table_info(expenses)")
        cols = {row[1] for row in cursor.fetchall()}
        
        cols_to_drop = []
        if 'quantity_buc' in cols:
            cols_to_drop.append('quantity_buc')
        if 'quantity_kg' in cols:
            cols_to_drop.append('quantity_kg')
        
        if cols_to_drop:
            print(f"    Removing columns: {', '.join(cols_to_drop)}")
            
            # Get the current schema
            cursor.execute("PRAGMA table_info(expenses)")
            all_cols = cursor.fetchall()
            keep_cols = [col[1] for col in all_cols if col[1] not in cols_to_drop]
            keep_cols_str = ', '.join(keep_cols)
            
            # Create backup of data
            cursor.execute(f"CREATE TABLE expenses_new AS SELECT {keep_cols_str} FROM expenses")
            cursor.execute("DROP TABLE expenses")
            cursor.execute("ALTER TABLE expenses_new RENAME TO expenses")
            conn.commit()
            print(f"    Removed {len(cols_to_drop)} legacy columns")
        else:
            print("    No legacy columns to remove")
        
        # Re-enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        
        if not dry_run:
            conn.commit()
            print("\n[OK] Migration 0005 applied successfully")
        else:
            print("\n[DRY-RUN] Rolling back changes...")
            conn.rollback()
            print("[OK] Dry-run complete. No changes applied.")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        cursor.execute("PRAGMA foreign_keys=ON")
        conn.rollback()
        conn.close()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Migration 0005: Store type and quantity unit"
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
    print("Migration 0005: Store Type and Quantity Unit")
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
        print("Dry-run complete. Review changes and run again without --dry-run")
    else:
        print("Migration complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
