import json

import requests

BASE = "http://127.0.0.1:8000/api/v1"

resp = requests.post(
    f"{BASE}/auth/login",
    data={"username": "manager@poc07.com", "password": "Password@123"},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

products = requests.get(f"{BASE}/products", headers=headers).json()
targets = {"Basmati Rice 5kg", "Gaming Laptop", "Samsung Galaxy Mobile"}
selected = [p for p in products if p["name"] in targets]
print(json.dumps(selected, indent=2))

with open("_validation_token.txt", "w", encoding="ascii") as fh:
    fh.write(token)

with open("_validation_products.json", "w", encoding="utf-8") as fh:
    json.dump(selected, fh)
