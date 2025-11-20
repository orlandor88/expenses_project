## Expenses Project — Documentation

Last updated: 2025-11-20

This document explains the structure, purpose, and operational details of the Expenses Project in plain language so collaborators (developers, maintainers, auditors) can understand and operate the codebase.

## Table of contents

- Project overview
- Quick start (run locally)
- Repository layout
- Database schema (current)
- Migrations and backup policy
- Important scripts (what they do)
- Web application: endpoints and client behavior
- Templates and JavaScript features
- Development notes, testing and verification
- Troubleshooting & common issues
- Next steps and recommended improvements


## Project overview

This is a small Flask-based web application that tracks expenses (line items) and groups them optionally into receipts (receipt headers). Key features implemented:

- Single-page receipt entry: header (store, nr_bon, date) + multiple line items (product, price, quantity, discount in lei) without navigating away.
- Product typeahead (create-on-the-fly product option) and product/category normalization.
- Per-line discount in lei (stored on each expense line) and server-side total calculation.
- Migration scripts to move from numeric receipt IDs to text `nr_bon` primary keys and to populate `expenses.receipt_nr`.
- Safety-first migration workflow with backups written outside the repository and pre-migration checks.


## Quick start (run locally)

Prerequisites:
- Python 3.9+ (use the project's environment or a virtualenv)
- SQLite (bundled with Python)

Basic steps to run locally (bash):

```bash
# create and activate a virtualenv (optional but recommended)
python -m venv .venv
source .venv/Scripts/activate   # on Windows Bash: .venv/Scripts/activate
pip install -r requirements.txt  # if requirements.txt exists; otherwise install Flask

# run the app (development)
# app_web.py is the primary entrypoint for the web UI
python app_web.py

# visit http://127.0.0.1:5000/ in your browser
```

Notes:
- If you run migrations, stop the running web app first. Migration scripts include a `.--force` override but stopping the app is safest.
- Backups are saved to the external folder `expenses_backups/` (created adjacent to the repo root by migration scripts).


## Repository layout

Top-level files and folders (short description):

- `app.py`, `app_web.py` — Flask application modules; `app_web.py` is the active web-facing server used during most work (contains routes and AJAX endpoints for receipts/expenses).
- `init_db.py`, `delete_database.py` — helper scripts to initialize or wipe the database.
- `bonuri/`, `processed/` — (project-specific folders, contain receipts or input data processed by older tooling)
- `old/` — previous/experimental versions of receipt scanning and manual-entry scripts.
- `static/` — CSS and static assets used by templates (e.g., `style.css`).
- `templates/` — Jinja2 HTML templates used to render pages; important templates include `record_expense.html` and `cheltuieli.html`.
- `scripts/` — migration and helper scripts (see details below).
- `PROJECT_DOCUMENTATION.md` — this file (project-wide documentation).
- `expenses.db` — SQLite database file (not committed if you follow .gitignore rules).


## Database schema (current)

The app uses SQLite. The primary tables (as used today) are:

- `products` (id INTEGER PRIMARY KEY, name TEXT, store_id INTEGER?, category_id INTEGER?, ...)
- `categories` (id INTEGER PRIMARY KEY, name TEXT, ...)
- `stores` (id INTEGER PRIMARY KEY, name TEXT, ...)
- `receipts` (nr_bon TEXT PRIMARY KEY, store_id INTEGER, date TEXT, extra columns...)
- `receipts_old` (kept temporarily by migration scripts; contains a copy of the old receipts table for verification)
- `expenses` (id INTEGER PRIMARY KEY, product_id INTEGER, store_id INTEGER, price REAL, quantity REAL, discount REAL, receipt_nr TEXT, ...)

Key details:
- `receipts.nr_bon` is a TEXT primary key (the receipt number) introduced by migration 0004.
- Each expense line may reference `receipt_nr` (string) to indicate it belongs to a receipt header in `receipts`.
- `discount` in `expenses` stores a per-line discount in lei (real), not a percentage. The total for a line is computed as (price * quantity - IFNULL(discount,0)) on the server.


## Migrations and backup policy

Important files:
- `scripts/migrate_0003_receipts.py` — earlier migration script (may exist in `scripts/` history)
- `scripts/migrate_0004_receipts_nrbon.py` — migration that converts receipt primary key to `nr_bon` (TEXT) and populates `expenses.receipt_nr` from the old numeric id.

Migration policy and behavior:
- Migrations create backups before altering any data.
- Backups are written to an external folder `expenses_backups/` adjacent to the repo root (e.g., `F:/Proiecte_CV/expenses_backups/`) so repository history isn't polluted with large binary backups.
- Migration scripts attempt to detect if the web app is running (via `psutil` when available, or by probing common ports 5000/8000/8080). They refuse to run if the app appears to be active unless `--force` is used.
- Migrations set a connection timeout and issue `PRAGMA busy_timeout = 30000` to tolerate transient database locks.

Verification practice:
- After running the migration, examine the `receipts` table and check whether `expenses.receipt_nr` values were set. A helper script `scripts/show_migrated_receipts.py` was added to list receipts for verification.
- Migration leaves `receipts_old` behind for audit; drop it only after you're confident.


## Important scripts (what they do)

This section enumerates the key scripts in `scripts/` and top-level helpers.

- `scripts/migrate_0004_receipts_nrbon.py` — Primary migration to convert `receipts` primary key to `nr_bon` (TEXT) and add/populate `expenses.receipt_nr`.
  - Creates an external backup before DDL changes.
  - Creates `receipts_new` with `nr_bon TEXT PRIMARY KEY`.
  - Copies rows from old receipts, generating `AUTO-{old_id}` when `nr_bon` missing.
  - Adds `receipt_nr` column to `expenses` and populates it using the old `receipt_id` mapping.
  - Renames `receipts` → `receipts_old` and `receipts_new` → `receipts`.
  - Performs safe PRAGMA changes and long busy_timeout to reduce "database is locked" errors.
  - Includes detection of running app processes and port probes; has `--force` override.

- `scripts/show_migrated_receipts.py` — Helper to list or sample receipts after migration for verification.

- `scripts/smoke_test_receipt.py` — (if present) a smoke test intended to create a test receipt and add items. Note: earlier use of fixed test keys caused collisions; update the script to generate unique `nr_bon` values (timestamp/UUID) before running.

- `init_db.py` — initialize a fresh database schema (use with care). It may create initial tables and seed basic rows.

- `delete_database.py` — deletes the database file; used for local resets.

- Old scripts in `old/` — various scanning and manual entry utilities for receipt OCR/processing. Keep as reference, not for production use.


## Web application: endpoints and client behavior

The web app is implemented with Flask. `app_web.py` is the main server script used in recent work. It contains routes providing HTML pages and JSON endpoints used by the single-page receipt UI.

Key endpoints (approximate names and behavior):

- GET `/` or `/index` — landing page; simplified index.
- GET `/record_expense` — page used for single-page receipt entry (renders `templates/record_expense.html`).
- POST `/create_receipt` — create a new receipt header (store, nr_bon, date). Returns JSON with receipt id / nr_bon.
- POST `/add_line_item` — adds an expense line to a receipt (product_id or product name, price, quantity, discount). Creates product on-the-fly if needed. Returns JSON representing the inserted line (rounded numeric fields).
- POST `/update_expense` — update an existing expense line; recalculates totals server-side, returns rounded JSON.
- POST `/delete_expense` — deletes an expense line. Implemented with an undo flow in the UI (server may keep soft-deletes or fully deletes depending on the endpoint used).
- POST `/complete_receipt` or `/close_receipt` — marks a receipt as complete/finalized. The UI calls this when the user finishes entering lines.
- GET `/cheltuieli` — list view grouped by receipt, and separate ungrouped expenses.

Server-side processing notes:
- Totals are computed server-side as (price * quantity - IFNULL(discount,0)). JSON endpoints typically return rounded numeric values to 2 decimal places to avoid float display surprises.
- Server enforces store name uppercase normalization and prevents duplicate stores/products where appropriate.


## Templates and JavaScript features

Important templates and client behaviors:

- `templates/record_expense.html`:
  - Presents a header area to enter `store`, `nr_bon` (receipt number), and `date`.
  - Presents an inline form to add multiple lines (product, price, quantity, discount in lei).
  - Uses a product typeahead to search existing products. If a product isn't found, the UI allows creating it on-the-fly.
  - Each added line appears in a list with edit/delete controls. Deleting a line triggers an undo toast to allow quick recovery.
  - Completing the receipt calls `complete_receipt` endpoint and optionally redirects to the receipts list.

- `templates/cheltuieli.html`:
  - Displays receipts grouped by `nr_bon` header. Each receipt shows its lines and totals.
  - Ungrouped expense lines (that don't reference a receipt) are shown separately.
  - Numeric values (price, quantity, discount, total) are formatted to two decimals using Jinja2 formatting and server-side rounding.

Client-side JavaScript behaviors:
- Typeahead with debounce and keyboard navigation (arrow keys, enter to select).
- Debounced server calls for product suggestion.
- AJAX `fetch()` calls to create receipts and add/edit/delete lines.
- Inline validation for numeric values and simple error handling (displaying server errors when returned as JSON).


## Development notes, testing and verification

- Push changes to a feature branch (e.g., `orlando`) and open a PR to `master` when ready.
- Migration safety:
  - Stop the web app before running migration when possible.
  - Migration scripts will create backups in `expenses_backups/` automatically. Keep these until you're comfortable dropping `receipts_old`.
- Smoke tests:
  - Update `scripts/smoke_test_receipt.py` to generate unique `nr_bon` values (use timestamp or UUID) to avoid collisions.
  - Add unit tests for new endpoints (`/create_receipt`, `/add_line_item`, `/update_expense`) if you later introduce a test runner (pytest).
- Quick verification commands (Python snippets):
  - To list receipts and count linked expenses:

```python
import sqlite3
con = sqlite3.connect('expenses.db')
cur = con.cursor()
for row in cur.execute("SELECT nr_bon, count(e.id) as expense_count FROM receipts r LEFT JOIN expenses e ON e.receipt_nr = r.nr_bon GROUP BY r.nr_bon ORDER BY r.nr_bon LIMIT 50"):
    print(row)
con.close()
```


## Troubleshooting & common issues

1. "sqlite3.OperationalError: database is locked"
   - Cause: the DB is busy (another process, e.g., the running Flask app, is using it).
   - Fix: stop the app and re-run the migration. Migration script sets a busy timeout, but stopping the web app is safest.

2. Duplicate test collisions in smoke tests
   - Cause: fixed test `nr_bon` reused across runs and already exists.
   - Fix: update the test to create unique `nr_bon` values using timestamps or UUIDs.

3. Missing `expense.receipt_nr` after migration
   - Cause: migration failed part-way or didn't complete due to lock/error.
   - Fix: consult the migration backup in `expenses_backups/`, restore the pre-migration DB and re-run migration after stopping the app.

4. Backup files appearing in git
   - If backups were accidentally committed, remove them and update `.gitignore` (the project already includes rules to ignore `expenses_backups/` and SQLite journal/wal/shm files).


## Next steps and recommended improvements

- Add automated tests (pytest) for the new endpoints and for migration scripts. Include a small fixture DB used for testing so migrations can be executed in CI safely.
- Extend `scripts/show_migrated_receipts.py` to produce a verification report comparing `receipts_old` vs `receipts` and listing rows where mapping is ambiguous.
- Add a small admin page listing backup files and checksums to simplify auditing.
- Replace direct SQL string concatenation (if any) with parameterized queries everywhere; audit for SQL injection risk if user input ever reaches raw SQL.
- Consider moving from SQLite to a server-backed DB (Postgres) for concurrent use and to ease migrations in multi-user setups.


## Contact and authorship

- Primary developer: Orlando (local branch `orlando`) — see commit history in git for exact authorship and commit messages.
- For questions about migration history or to request a rollback, check the `expenses_backups/` folder for timestamped backups.


## Verification summary (state as of this document)

- Migration to `receipts.nr_bon` applied (migration script `scripts/migrate_0004_receipts_nrbon.py`). A `receipts_old` copy is retained for verification.
- Backups were moved to `F:/Proiecte_CV/expenses_backups/` and `.gitignore` updated to ignore them and transient DB files.
- An extraneous empty receipt `00253` was removed and the suffixed receipt `00253-1763570283` was renamed back to `00253` with its expense rows updated after making a local pre-rename backup.


---

If you'd like, I can also:
- Add a smaller `README.md` with quick start instructions at the repo root.
- Expand individual script documentation into separate files under `docs/scripts/` (one file per script) with input/output examples and sample runs.
- Generate a `requirements.txt` or a `pyproject.toml` if you want to standardize the environment.

Tell me which of the follow-ups you'd like me to do next.