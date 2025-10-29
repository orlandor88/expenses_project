import os
import re
import sqlite3
import shutil
from PIL import Image
import pytesseract
import cv2

# === SETĂRI TESSERACT ===
# Ajustează după locația ta reală:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\TesseractData\tessdata"  # folderul unde ai ron.traineddata

# === FOLDERE FIXE ===
INPUT_FOLDER = r"F:\Proiecte_CV\expenses_project\bonuri"
PROCESSED_FOLDER = os.path.join(INPUT_FOLDER, "processed")
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# === FUNCȚIE PREPROCESARE IMAGINE ===
def preprocess_image(path):
    img = cv2.imread(path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # CLAHE — contrast local
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    # adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    # salvează imagine temporară
    base, ext = os.path.splitext(path)
    proc_path = base + "_proc.jpg"
    cv2.imwrite(proc_path, thresh)
    return proc_path

# === FUNCȚIE DETECTARE „TOTAL / SUMĂ” ===
def extract_total_smart(text):
    text_norm = text.replace("\n", " ").replace(",", ".")
    keywords = ["total", "sumă de plată", "de plată", "total de plată"]
    for kw in keywords:
        # căutăm cuvânt-cheie urmat de cifră
        pattern = rf"{kw}[:\s]*([0-9]+(?:\.[0-9]+)?)"
        matches = re.findall(pattern, text_norm, re.IGNORECASE)
        if matches:
            return matches[-1]
    # fallback: ultima cifră detectată din tot textul
    nums = re.findall(r"[0-9]+(?:\.[0-9]+)?", text_norm)
    if nums:
        return nums[-1]
    return None

# === SALVARE ÎN BAZA DE DATE ===
def save_to_db(file_name, total):
    conn = sqlite3.connect("expenses.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file TEXT,
            total REAL
        )
    """)
    cur.execute("INSERT INTO expenses (file, total) VALUES (?, ?)", (file_name, float(total)))
    conn.commit()
    conn.close()

# === SCAN FOLDER ===
def scan_folder():
    images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not images:
        print("❌ Nu s-au găsit imagini în folderul de intrare.")
        return

    for imgfile in images:
        full_path = os.path.join(INPUT_FOLDER, imgfile)
        print(f"\n📸 Procesare: {full_path}")

        # Preprocesare
        proc_path = preprocess_image(full_path)
        if proc_path is None:
            print("⚠️ Nu s-a putut citi imaginea.")
            # mutăm fișierul oricum în processed
            shutil.move(full_path, os.path.join(PROCESSED_FOLDER, imgfile))
            continue

        # OCR pe imagine procesată
        img = Image.open(proc_path)
        text = pytesseract.image_to_string(img, lang="ron+eng", config="--psm 6")

        print("=== Text detectat (fragment) ===")
        print(text[:200], "...")

        total = extract_total_smart(text)
        if total:
            print(f"✅ Suma detectată: {total} lei")
            save_to_db(imgfile, total)
        else:
            print("⚠️ Nu s-a detectat suma totală.")

        # Mută imaginea originală în processed
        dst = os.path.join(PROCESSED_FOLDER, imgfile)
        shutil.move(full_path, dst)

        # Și, opțional, șterge imaginea procesată temporară
        try:
            os.remove(proc_path)
        except Exception as e:
            pass

if __name__ == "__main__":
    scan_folder()
