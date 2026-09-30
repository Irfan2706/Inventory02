import json

import requests

BASE = "http://127.0.0.1:8000/api/v1"

with open("_validation_token.txt", "r", encoding="ascii") as fh:
    token = fh.read().strip()

headers = {"Authorization": f"Bearer {token}"}

targets = {"Basmati Rice 5kg": 5, "Gaming Laptop": 10, "Samsung Galaxy Mobile": 12}
results = {}
for name, product_id in targets.items():
    resp = requests.post(f"{BASE}/multi-agent/analyze", json={"product_id": product_id}, headers=headers)
    results[name] = {"status_code": resp.status_code, "body": resp.json()}

with open("_validation_results.json", "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2)

print(json.dumps(results, indent=2))
