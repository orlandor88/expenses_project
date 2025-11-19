#!/usr/bin/env python3
"""
Migration 0004: Make receipts primary key be nr_bon (TEXT) and populate expenses.receipt_nr.

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
        import argparse
        import socket

        BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DB = os.path.join(BASE, 'expenses.db')


        def is_port_open(host, port, timeout=0.5):
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except Exception:
                return False


        def detect_running_app():
            """Return a list of candidate processes/ports that indicate the app might be running."""
            findings = []
            # Try psutil if available to find python/flask processes running the app
            try:
                import psutil
                for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmd = ' '.join(p.info.get('cmdline') or [])
                        name = (p.info.get('name') or '').lower()
                        if 'flask' in cmd.lower() or 'flask' in name or 'app_web.py' in cmd or 'app.py' in cmd:
                            findings.append(('proc', p.info.get('pid'), cmd or name))
                    except Exception:
                        continue
            except Exception:
                # psutil not present — skip process inspection
                pass

            # Fallback: check common Flask ports (5000, 8000, 8080)
            for port in (5000, 8000, 8080):
                if is_port_open('127.0.0.1', port):
                    findings.append(('port', port, '127.0.0.1:%d' % port))

            return findings


        def main():
            parser = argparse.ArgumentParser(description='Migrate receipts to use nr_bon TEXT PK (migration 0004)')
            parser.add_argument('--force', action='store_true', help='Force migration even if app detection finds a running server')
            args = parser.parse_args()

            if not os.path.exists(DB):
                print('No expenses.db found at', DB)
                sys.exit(1)

            if not args.force:
                findings = detect_running_app()
                if findings:
                    print('\nDetected possible running application (server/process). Aborting migration to avoid corrupting live DB.')
                    for f in findings:
                        if f[0] == 'proc':
                            print(f' - process pid={f[1]} cmd="{f[2]}"')
                        else:
                            print(f' - port open: {f[2]}')
                    print('\nIf you are sure no app is running, re-run with --force to proceed.')
                    sys.exit(2)

            bak = DB + '.bak_mig0004'
            print('Creating backup:', bak)
            shutil.copy2(DB, bak)

            # Open DB connection with a longer timeout and set busy_timeout to reduce 'database is locked' errors
            conn = sqlite3.connect(DB, timeout=30)
            cur = conn.cursor()
            try:
                cur.execute('PRAGMA busy_timeout = 30000')
            except Exception:
                pass

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


        if __name__ == '__main__':
            main()
