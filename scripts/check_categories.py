import sqlite3

db = r'F:/Proiecte_CV/expenses_project/expenses.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT id, categorie FROM categorii ORDER BY categorie")
rows = cur.fetchall()
print('Total categories:', len(rows))
for r in rows:
    print(r[0], '|', r[1])

cur.execute("SELECT id, categorie FROM categorii WHERE LOWER(categorie)=?", ('medicamente',))
found = cur.fetchone()
print('\nSearch for medicamente ->', found)
conn.close()
