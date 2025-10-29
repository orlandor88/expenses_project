import sqlite3
from datetime import datetime

# === 1. Deschidem / creăm baza de date ===
conn = sqlite3.connect("expenses.db")
cursor = conn.cursor()

# === 2. Creăm tabelul dacă nu există ===
cursor.execute("""
CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_bon TEXT,
    denumire_produs TEXT,
    cantitate REAL,
    pret REAL
)
""")
conn.commit()

print("📅 Introdu datele bonului fiscal (apasă Enter fără text pentru a opri introducerea produselor).")

# === 3. Data bonului ===
data_bon = input("Data bonului (format YYYY-MM-DD, Enter pentru azi): ").strip()
if not data_bon:
    data_bon = datetime.now().strftime("%Y-%m-%d")

produse_introduse = []

# === 4. Funcție pentru afișarea produselor existente ===
def get_produse_existente():
    cursor.execute("SELECT DISTINCT denumire_produs FROM receipts ORDER BY denumire_produs")
    return [row[0] for row in cursor.fetchall()]

# === 5. Introducem produsele ===
while True:
    produse_existente = get_produse_existente()

    if produse_existente:
        print("\n📦 Produse existente (selectează numărul sau scrie un nume nou):")
        for i, p in enumerate(produse_existente, start=1):
            print(f"  {i}. {p}")

    denumire = input("\nDenumire produs (Enter pentru a termina): ").strip()
    if not denumire:
        break

    # Dacă utilizatorul a introdus un număr, îl interpretăm ca selecție din listă
    if denumire.isdigit():
        idx = int(denumire) - 1
        if 0 <= idx < len(produse_existente):
            denumire = produse_existente[idx]
            print(f"✅ Ai selectat produsul existent: {denumire}")
        else:
            print("⚠️ Număr invalid. Se va considera produs nou.")

    try:
        cantitate = float(input("Cantitate: ").strip().replace(",", "."))
    except ValueError:
        cantitate = 1.0

    try:
        pret = float(input("Preț (RON): ").strip().replace(",", "."))
    except ValueError:
        pret = 0.0

    # Inserăm produsul
    cursor.execute("""
        INSERT INTO receipts (data_bon, denumire_produs, cantitate, pret)
        VALUES (?, ?, ?, ?)
    """, (data_bon, denumire, cantitate, pret))
    conn.commit()

    produse_introduse.append((denumire, cantitate, pret))
    print(f"✅ Adăugat: {denumire} - {cantitate} x {pret:.2f} RON")

# === 6. Afișăm recapitularea ===
if produse_introduse:
    print("\n📋 Produsele introduse pe bonul din", data_bon)
    print("-" * 50)
    print(f"{'Produs':25} {'Cant.':>7} {'Preț (RON)':>12}")
    print("-" * 50)
    for p in produse_introduse:
        print(f"{p[0]:25} {p[1]:7.2f} {p[2]:12.2f}")
    print("-" * 50)
    total = sum(p[2] for p in produse_introduse)
    print(f"{'TOTAL':25} {'':7} {total:12.2f} RON\n")
else:
    print("⚠️ Nu a fost introdus niciun produs.")

# === 7. Mini-raport lunar ===
def raport_lunar():
    luna_curenta = datetime.now().strftime("%Y-%m")
    print(f"📊 Raport lunar pentru {luna_curenta}")
    print("=" * 55)

    cursor.execute("""
        SELECT denumire_produs,
               SUM(cantitate) AS total_cantitate,
               SUM(pret) AS total_pret
        FROM receipts
        WHERE strftime('%Y-%m', data_bon) = ?
        GROUP BY denumire_produs
        ORDER BY total_pret DESC
    """, (luna_curenta,))

    rows = cursor.fetchall()
    if not rows:
        print("⚠️ Nu există date pentru luna curentă.")
        return

    total_general = 0
    print(f"{'Produs':25} {'Cant.':>8} {'Total (RON)':>15}")
    print("-" * 55)
    for r in rows:
        produs, cant, pret = r
        total_general += pret
        print(f"{produs:25} {cant:8.2f} {pret:15.2f}")
    print("-" * 55)
    print(f"{'TOTAL GENERAL':25} {'':8} {total_general:15.2f} RON")

# Afișăm raportul lunar
raport_lunar()

conn.close()
