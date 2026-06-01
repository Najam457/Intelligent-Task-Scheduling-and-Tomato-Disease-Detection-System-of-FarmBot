import requests
import cv2
import numpy as np
import cloudinary
import cloudinary.uploader

# CONFIGURATION

EMAIL = "najams457@gmail.com"
PASSWORD = "najamhasan"

ROBOFLOW_API_KEY = "KcibZsXZeBTj5EThHZvQ"
MODEL_URL = "https://classify.roboflow.com/tomato-disease-ai/1"

CLOUD_NAME = "dektd20z7"
CLOUD_API_KEY = "597533235782979"
CLOUD_API_SECRET = "FM7EFFNoXMBKJSCyLSQ10y4VX08"

OUTPUT_IMAGE = "final_output.jpg"
IMAGE_PATH = "latest_plant.jpg"

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=CLOUD_API_KEY,
    api_secret=CLOUD_API_SECRET
)

# STEP 1 — LOGIN FARMBOT

print("Logging into FarmBot...")

token_res = requests.post(
    "https://my.farm.bot/api/tokens",
    json={"user": {"email": EMAIL, "password": PASSWORD}}
)

data = token_res.json()
TOKEN = data["token"]["encoded"]

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("FarmBot login success")

# STEP 2 — GET LATEST IMAGE

print("Fetching image...")

img_res = requests.get(
    "https://my.farm.bot/api/images",
    headers=headers
)

images = img_res.json()

if not images:
    print("No images found")
    exit()

image_url = images[0]["attachment_url"]

img_data = requests.get(image_url).content

with open(IMAGE_PATH, "wb") as f:
    f.write(img_data)

# STEP 3 — LOAD IMAGE

image = cv2.imread(IMAGE_PATH)

if image is None:
    print("Image load failed")
    exit()

image = cv2.resize(image, (600, 600))
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# STEP 4 — LEAF DETECTION (GATEKEEPER)

lower_green = np.array([35, 40, 40])
upper_green = np.array([90, 255, 255])

lower_yellow = np.array([15, 40, 40])
upper_yellow = np.array([35, 255, 255])

green_mask = cv2.inRange(hsv, lower_green, upper_green)
yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

green = np.sum(green_mask > 0)
yellow = np.sum(yellow_mask > 0)

total = green + yellow

if total == 0:
    msg = "No plant detected. Process stopped."

    requests.post(
        "https://my.farm.bot/api/logs",
        headers=headers,
        json={"message": msg, "type": "warn", "channels": ["toast"]}
    )

    print(msg)
    exit()

green_ratio = round((green / total) * 100, 2)

if green_ratio > 75:
    health = "Healthy"
elif green_ratio > 50:
    health = "Moderate"
else:
    health = "Unhealthy"

# STEP 5 — DISEASE DETECTION

with open(IMAGE_PATH, "rb") as img:
    res = requests.post(
        MODEL_URL,
        params={"api_key": ROBOFLOW_API_KEY},
        files={"file": img}
    )

try:
    result = res.json()
except:
    result = {}

if "top" in result:
    disease = result["top"]
    confidence = result["confidence"]
else:
    disease = "Unknown"
    confidence = 0

confidence_percent = round(confidence * 100, 2)

if "___" in disease:
    _, disease_name = disease.split("___")
else:
    disease_name = disease

disease_name = disease_name.replace("_", " ")

# STEP 6 — VISUALIZATION (ONLY IF DISEASE STEP PASSED)

lower_disease = np.array([10, 40, 40])
upper_disease = np.array([35, 255, 255])

mask = cv2.inRange(hsv, lower_disease, upper_disease)

kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

contours, _ = cv2.findContours(
    mask,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

spots = 0
infected = 0

for c in contours:
    area = cv2.contourArea(c)

    if area > 500:
        spots += 1
        infected += area

        x, y, w, h = cv2.boundingRect(c)

        cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.putText(image, "Disease", (x, y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

image_area = image.shape[0] * image.shape[1]

severity_pct = round((infected / image_area) * 100, 2)

if severity_pct < 10:
    level = "Low"
elif severity_pct < 25:
    level = "Moderate"
else:
    level = "Severe"

# STEP 7 — SAVE & UPLOAD IMAGE

cv2.imwrite(OUTPUT_IMAGE, image)

upload = cloudinary.uploader.upload(OUTPUT_IMAGE)
image_url = upload["secure_url"]

# STEP 8 — FINAL REPORT

final_report = f"""
SMART PLANT REPORT

Health: {health}
Green: {green_ratio}%

Disease: {disease_name}
Confidence: {confidence_percent}%

Severity Level: {level}
Infected Spots: {spots}
Infected Area: {severity_pct}%

Image: {image_url}
"""

print(final_report)

# STEP 9 — FARMBOT LOG (SINGLE OUTPUT ONLY)

requests.post(
    "https://my.farm.bot/api/logs",
    headers=headers,
    json={
        "message": final_report,
        "type": "info",
        "channels": ["toast"]
    }
)

print("DONE")