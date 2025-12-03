# Migration Plan 0005 — Store Types, Quantity Units, Store Receipts Page

Last updated: 2025-12-03

This migration implements the TODOs listed in `changes.md`:

1. Add separate store types (pharmacy, supermarket, restaurant, gas station) and allow choosing a type when adding/updating stores.
2. Add separate columns for pieces (`quantity_buc`) and kilograms (`quantity_kg`) to `expenses`.
3. Add a new per-store receipts page/template that shows merged receipts for each store.

This document describes the steps, scripts, tests, and rollback guidance.

Summary of Changes
- DB:
  - Add `store_types` lookup table and populate with defaults.
  - Add `store_type_id` column to `stores` (nullable initially).
  - Add `quantity_type` (TEXT DEFAULT 'buc') column to `expenses` to store 'buc' or 'kg'.
  - (Optional) Add `products.unit_type` column to `products` to record a product's default unit.
- App code:
  - Update store create/update forms to include a store type selector.
  - Update `record_expense` template and JS to include a unit selector (buc/kg) per line.
  - Update server endpoints to write to `quantity_type` column based on user selection.
  - Add `GET /stores/<id>` route and `templates/store_receipts.html` to show receipts grouped/merged per store.
- Scripts:
  - Add migration script `scripts/migrate_0005_store_types_and_units.py` with `--dry-run` and `--force` flags.
  - Use `scripts/backup_db.py` to create a dated backup before applying DDL changes.

Detailed Steps

1) PREPARE
- Ensure working tree is clean and committed.
- Stop the Flask app (to avoid DB locks).
- Run a backup:

```bash
python scripts/backup_db.py --prefix pre_mig0005
```

2) MIGRATION SCRIPT (scripts/migrate_0005_store_types_and_units.py)
- Features:
  - `--dry-run`: report what will change without applying
  - `--force`: override running-app guard
  - Creates a dated backup (calls backup_db.py)
  - Uses `PRAGMA foreign_keys=ON` and `PRAGMA busy_timeout=30000`
- Actions performed:
  - Create table `store_types` if missing and insert default rows: Pharmacy, Supermarket, Restaurant, Gas Station.
  - ALTER TABLE stores ADD COLUMN store_type_id INTEGER (if missing).
  - ALTER TABLE expenses ADD COLUMN quantity_buc INTEGER DEFAULT 0 (if missing).
  - ALTER TABLE expenses ADD COLUMN quantity_kg REAL DEFAULT 0.0 (if missing).
  - Optionally add `products.unit_type` TEXT (if you want automatic conversion help).
  - Produce a CSV `migration_report_pre_mig0005_<ts>.csv` listing all `expenses` rows where `quantity` is non-zero and the script could not confidently map it to `buc` or `kg` (requires manual review).

3) DATA CONVERSION STRATEGY
- If `products.unit_type` exists and contains `buc` or `kg`, populate `expenses.quantity_type` with that value.
- Otherwise, leave `quantity_type` as DEFAULT ('buc') and list the rows in the report CSV for manual reconciliation.
- Leave legacy `quantity` column untouched until verification complete.

4) APP CODE CHANGES
- `app_web.py`:
  - Update `add_store_route`/UI to accept `store_type_id` and save it.
  - Update `get_stores()` to return `store_type` names (JOIN), as needed for display.
  - Update `add_line_item_route` and `add_expense_route` to accept a `unit` parameter or separate `quantity_buc/quantity_kg` fields. Write the values into the new columns and keep `quantity` for compatibility.
- `templates/record_expense.html`:
  - Add a unit selector next to quantity input (radio buttons or dropdown).
  - Send the selected unit ('buc' or 'kg') in the AJAX payload when adding a line.
- `templates/cheltuieli.html` and `templates/store_receipts.html`:
  - Use `quantity_type` to format quantities appropriately (e.g., "1.5 kg" vs "2 buc").

5) TESTING (Local)
- Run migration script in `--dry-run` mode and inspect the planned changes and generated CSV report.
- If comfortable, run the migration script (no `--dry-run`):

```bash
python scripts/migrate_0005_store_types_and_units.py
```

- Start the app and manually create receipts and lines using both `buc` and `kg` units.
- Verify DB rows in `expenses` show the new columns populated appropriately.
- Run updated smoke tests (script should be updated to use unique `nr_bon` and include unit selections).

6) ROLLBACK
- If migration has issues, restore the backup created earlier. Example:

```bash
# Stop the app
# Copy backup file over expenses.db (use the exact backup filename printed by script)
cp ../expenses_backups/pre_mig0005_YYYYMMDD_HHMMSS.db expenses.db
```

- Re-open the bug report and inspect the migration report CSV to fix problematic rows before re-running migration.

7) DEPLOYMENT
- Merge the migration branch into `master` and deploy code changes on the server.
- On production:
  - Stop the app
  - Run `python scripts/backup_db.py --prefix pre_mig0005_prod`
  - Run migration script
  - Start the app and run verification smoke tests

Implementation checklist
- [ ] Create `scripts/migrate_0005_store_types_and_units.py` (dry-run, backup, --force)
- [ ] Update `app_web.py` to accept and persist `store_type_id` and unit-aware quantity
- [ ] Update `templates/record_expense.html` and client JS to send unit
- [ ] Add `templates/store_receipts.html` and route `GET /stores/<id>` that lists receipts merged for that store
- [ ] Update smoke tests and run them locally
- [ ] Run migration in staging/prod following the steps above

Notes & open questions
- How should `quantity` be mapped automatically? Best to ask product owners if possible; otherwise create the migration report and reconcile manually.
- If you prefer a simpler approach, instead of adding separate columns we could add a `unit` column and keep `quantity` (less schema churn) — but your request explicitly asked for separate columns.

If you want I can:
- Draft the actual Python migration script `scripts/migrate_0005_store_types_and_units.py` (with dry-run and backup support).
- Modify the templates/JS and `app_web.py` changes in a dedicated branch and run local smoke tests.

---

Ready to proceed — tell me whether you want me to implement the migration script now, or prepare the UI/server changes first.