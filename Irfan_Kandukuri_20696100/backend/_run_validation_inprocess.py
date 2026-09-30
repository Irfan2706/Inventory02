import json

from multi_agent import agents
from multi_agent.graph import analyze_product

with open("_validation_token.txt", "r", encoding="ascii") as fh:
    token = fh.read().strip()

targets = {"Basmati Rice 5kg": 5, "Gaming Laptop": 10, "Samsung Galaxy Mobile": 12}
results = {}
for name, product_id in targets.items():
    token_state = agents.set_api_token(f"Bearer {token}")
    try:
        result = analyze_product(product_id)
    finally:
        agents.reset_api_token(token_state)
    results[name] = result

with open("_validation_results.json", "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, default=str)

print(json.dumps(results, indent=2, default=str))
