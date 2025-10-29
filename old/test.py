import cv2

img = cv2.imread(r"F:\Proiecte_CV\expenses_project\bon_mega.jpg")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Aplică CLAHE
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)

# Binarizare adaptivă
thresh = cv2.adaptiveThreshold(
    enhanced, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    11, 2
)

cv2.imwrite("bon_enhanced.jpg", thresh)
