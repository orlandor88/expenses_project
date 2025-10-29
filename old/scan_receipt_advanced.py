import cv2
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from PIL import Image
import re
import sqlite3
from datetime import date


# === CONFIGURARE ===
DB_PATH = "expenses.db"

# === CONECTARE BAZĂ DE DATE ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# === FUNCȚIE DE CURĂȚARE IMAGINE ===
def preprocess_image(image_path):
    img = cv2.imread(image_path)

    # Convertim la gri
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aplicăm un filtru pentru reducerea zgomotului
    gray = cv2.medianBlur(gray, 3)

    # Binarizare adaptivă (face textul mai clar)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )

    # Salvăm imaginea temporar
    temp_path = "processed_receipt.png"
    cv2.imwrite(temp_path, thresh)
    return temp_path

# === FUNCȚIE DE ANALIZĂ TEXT ===
def extract_data_from_text(text):
    # Caută totalul
    total_match = re.search(r"TOTAL[:\s]*([0-9]+[.,][0-9]+)", text, re.IGNORECASE)
    amount = float(total_match.group(1).replace(",", ".")) if total_match else None

    # Caută data (format dd.mm.yyyy)
    date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    receipt_date = date_match.group(1) if date_match else date.today().isoformat()

    return amount, receipt_date

# === FUNCȚIE PRINCIPALĂ ===
def scan_receipt(image_path):
    print(f"🔍 Prelucrare imagine: {image_path}")
    processed_path = preprocess_image(image_path)

    # Extragem textul
    text = pytesseract.image_to_string(Image.open(processed_path), lang="ron")

    print("\n=== Text detectat (fragment) ===")
    print(text[:500])  # afișăm primele 500 de caractere pentru verificare

    # Extragem datele
    amount, receipt_date = extract_data_from_text(text)
    if amount:
        cursor.execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (receipt_date, "Cumpărături", "Bon scanat OCR", amount)
        )
        conn.commit()
        print(f"✅ Bon salvat în baza de date: {amount:.2f} lei (data: {receipt_date})")
    else:
        print("⚠️ Nu s-a putut identifica suma totală. Verifică claritatea imaginii.")

# === EXECUTARE ===
if __name__ == "__main__":
    path = input("📸 Introdu calea către imaginea bonului: ")
    scan_receipt(path)
