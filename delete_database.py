import os

DB_NAME = "expenses.db"

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)
    print(f"🗑️ Baza de date '{DB_NAME}' a fost ștearsă cu succes.")
else:
    print(f"⚠️ Baza de date '{DB_NAME}' nu există sau a fost deja ștearsă.")

DB_NAME = "products.db"

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)
    print(f"🗑️ Baza de date '{DB_NAME}' a fost ștearsă cu succes.")
else:
    print(f"⚠️ Baza de date '{DB_NAME}' nu există sau a fost deja ștearsă.")
   
