import sqlite3
from datetime import datetime

# === 1. Creăm (sau deschidem) baza de date ===
conn = sqlite3.connect("expenses.db")
cursor = conn.cursor()

# === 2. Creăm tabelul dacă nu există deja ===
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

# === 3. Cerem utilizatorului data bonului ===
data_bon = input("Data bonului (format YYYY-MM-DD, Enter pentru azi): ").strip()
if not data_bon:
    data_bon = datetime.now().strftime("%Y-%m-%d")

produse = []

# === 4. Introducem produsele manual ===
while True:
    denumire = input("\nDenumire produs (Enter pentru a termina): ").strip()
    if not denumire:
        break

    try:
        cantitate = float(input("Cantitate: ").strip().replace(",", "."))
    except ValueError:
        cantitate = 1.0

    try:
        pret = float(input("Preț (RON): ").strip().replace(",", "."))
    except ValueError:
        pret = 0.0

    # Salvăm produsul în baza de date
    cursor.execute("""
        INSERT INTO receipts (data_bon, denumire_produs, cantitate, pret)
        VALUES (?, ?, ?, ?)
    """, (data_bon, denumire, cantitate, pret))
    conn.commit()

    produse.append((denumire, cantitate, pret))
    print(f"✅ Adăugat: {denumire} - {cantitate} x {pret:.2f} RON")

# === 5. Afișăm produsele introduse ===
if produse:
    print("\n📋 Produsele introduse pe bonul din", data_bon)
    print("-" * 50)
    print(f"{'Produs':25} {'Cant.':>7} {'Preț (RON)':>12}")
    print("-" * 50)
    for p in produse:
        print(f"{p[0]:25} {p[1]:7.2f} {p[2]:12.2f}")
    print("-" * 50)
    total = sum(p[2] for p in produse)
    print(f"{'TOTAL':25} {'':7} {total:12.2f} RON\n")
else:
    print("⚠️ Nu a fost introdus niciun produs.")

conn.close()
