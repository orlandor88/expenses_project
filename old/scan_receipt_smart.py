from PIL import Image
import pytesseract
import os
import re
import sqlite3
import shutil

# === CONFIGURARE TESSERACT ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\TesseractData\tessdata"

# === Folderuri ===
INPUT_FOLDER = r"F:\Proiecte_CV\expenses_project\bonuri"
PROCESSED_FOLDER = os.path.join(INPUT_FOLDER, "processed")
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# === FUNCȚIE EXTRAGERE SUMĂ TOTALĂ INTELIGENTĂ ===
def extract_total_smart(text):
    """
    Caută cifre aproape de cuvinte-cheie, ignorând spații sau caractere speciale
    """
    # Normalizează textul
    text = text.replace("\n", " ").replace(",", ".")
    
    # Cuvinte-cheie posibile
    keywords = ["total", "sumă de plată", "de plată", "total de plată"]

    # Caută fiecare keyword și cifrele după
    for kw in keywords:
        pattern = rf"{kw}[:\s]*([0-9]+(?:\.[0-9]+)?)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[-1]  # ultima apariție

    # Dacă nu s-a găsit cuvânt-cheie, încearcă să ia ultima cifră mare din text
    numbers = re.findall(r"[0-9]+(?:\.[0-9]+)?", text)
    if numbers:
        return numbers[-1]
    
    return None

# === FUNCȚIE SALVARE ÎN DB ===
def save_to_db(file_path, total):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file TEXT,
            total REAL
        )
    """)
    c.execute("INSERT INTO expenses (file, total) VALUES (?, ?)", (file_path, total))
    conn.commit()
    conn.close()

# === FUNCȚIE PRINCIPALĂ ===
def scan_folder(folder_path):
    if not os.path.exists(folder_path):
        print("❌ Folderul nu există!")
        return

    images = [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".png"))]
    if not images:
        print("❌ Nu s-au găsit imagini în folder.")
        return

    for img_file in images:
        path = os.path.join(folder_path, img_file)
        print(f"\n📸 Procesare: {path}")

        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="ron+eng", config="--psm 6")

        total = extract_total_smart(text)
        if total:
            print(f"✅ Suma detectată: {total} lei")
            save_to_db(img_file, total)
        else:
            print("⚠️ Nu s-a putut identifica suma totală. Verifică claritatea imaginii.")

        # Mută fișierul original în folderul processed
        shutil.move(path, os.path.join(PROCESSED_FOLDER, img_file))

# === RULARE SCRIPT ===
if __name__ == "__main__":
    scan_folder(INPUT_FOLDER)
