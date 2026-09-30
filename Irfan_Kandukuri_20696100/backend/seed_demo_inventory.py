"""Idempotent demo-data seeder for the dev database (backend/inventory.db).

Adds realistic suppliers/products/stock/movements for Phase 5 Multi-Agent
Mode UX testing, without touching or deleting any existing rows. Safe to
run multiple times: skips any supplier/product that already exists by name.

Usage: .venv\\Scripts\\python.exe seed_demo_inventory.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base, SessionLocal, engine
from app.models import Product, Supplier
from app.services import apply_stock_movement, generate_sku, upsert_stock_level
from app.models import MovementType

Base.metadata.create_all(bind=engine)

SUPPLIERS = [
    {"name": "Tech Distributors Pvt Ltd", "supplier_code": "TECH-DIST-001", "contact_email": "contact@techdistributors.com", "lead_time_days": 5, "payment_terms_days": 30},
    {"name": "FreshMart Wholesale", "supplier_code": "FRESHMART-001", "contact_email": "orders@freshmartwholesale.com", "lead_time_days": 3, "payment_terms_days": 15},
    {"name": "Home Essentials Supply", "supplier_code": "HOMEESS-001", "contact_email": "sales@homeessentialssupply.com", "lead_time_days": 7, "payment_terms_days": 30},
    {"name": "StyleWear Wholesale", "supplier_code": "STYLEWEAR-001", "contact_email": "info@stylewearwholesale.com", "lead_time_days": 10, "payment_terms_days": 45},
    {"name": "HealthCare Traders", "supplier_code": "HEALTHTR-001", "contact_email": "support@healthcaretraders.com", "lead_time_days": 6, "payment_terms_days": 30},
]

# (name, category, unit_price, cost_price, unit_of_measure, reorder_point, reorder_quantity,
#  supplier_name, final_available, daily_rate, trend)
PRODUCTS = [
    ("Basmati Rice 5kg", "grocery", 450.0, 350.0, "bag", 30, 150, "FreshMart Wholesale", 18, 3.0, "increasing"),
    ("Wheat Flour 10kg", "grocery", 380.0, 300.0, "bag", 25, 120, "FreshMart Wholesale", 90, 2.0, "stable"),
    ("Cooking Oil 1L", "grocery", 180.0, 140.0, "bottle", 40, 200, "FreshMart Wholesale", 42, 2.5, "stable"),
    ("Sugar 5kg", "grocery", 220.0, 170.0, "bag", 35, 150, "FreshMart Wholesale", 140, 2.0, "decreasing"),
    ("Toor Dal 2kg", "grocery", 260.0, 200.0, "bag", 25, 100, "FreshMart Wholesale", 24, 1.5, "increasing"),

    ("Gaming Laptop", "electronics", 95000.0, 78000.0, "unit", 5, 20, "Tech Distributors Pvt Ltd", 3, 0.5, "increasing"),
    ("Business Laptop", "electronics", 65000.0, 52000.0, "unit", 8, 25, "Tech Distributors Pvt Ltd", 22, 0.3, "stable"),
    ("Samsung Galaxy Mobile", "electronics", 32000.0, 26000.0, "unit", 10, 40, "Tech Distributors Pvt Ltd", 9, 0.8, "increasing"),
    ("iPhone", "electronics", 79000.0, 68000.0, "unit", 6, 20, "Tech Distributors Pvt Ltd", 18, 0.4, "stable"),
    ("Bluetooth Headphones", "electronics", 3500.0, 2200.0, "unit", 20, 80, "Tech Distributors Pvt Ltd", 75, 1.5, "stable"),

    ("Pressure Cooker", "household", 2200.0, 1600.0, "unit", 15, 60, "Home Essentials Supply", 40, 0.7, "stable"),
    ("Vacuum Cleaner", "household", 6500.0, 4800.0, "unit", 8, 30, "Home Essentials Supply", 7, 0.4, "increasing"),
    ("Water Bottle Set", "household", 850.0, 550.0, "set", 20, 100, "Home Essentials Supply", 95, 1.2, "stable"),

    ("Shampoo", "personal_care", 320.0, 220.0, "bottle", 30, 150, "HealthCare Traders", 110, 2.0, "stable"),
    ("Body Wash", "personal_care", 280.0, 190.0, "bottle", 30, 150, "HealthCare Traders", 33, 1.5, "stable"),
    ("Toothpaste", "personal_care", 120.0, 80.0, "tube", 40, 200, "HealthCare Traders", 180, 2.5, "stable"),

    ("Men T-Shirt", "clothing", 599.0, 350.0, "piece", 25, 120, "StyleWear Wholesale", 90, 1.5, "stable"),
    ("Women Jacket", "clothing", 1899.0, 1200.0, "piece", 12, 50, "StyleWear Wholesale", 45, 0.6, "decreasing"),
]

TREND_MULTIPLIERS = {
    "increasing": [0.7, 0.85, 1.0, 1.15],
    "decreasing": [1.3, 1.1, 0.9, 0.7],
    "stable": [1.0, 1.0, 1.0, 1.0],
}
SALE_DAYS_AGO = [12, 9, 6, 3]
RECEIPT_DAYS_AGO = 25


def build_movement_plan(final_available: int, daily_rate: float, trend: str) -> list[tuple[str, int, int]]:
    multipliers = TREND_MULTIPLIERS[trend]
    sale_quantities = [max(1, round(daily_rate * 3 * m)) for m in multipliers]
    total_sales = sum(sale_quantities)
    receipt_quantity = final_available + total_sales
    plan = [("receipt", receipt_quantity, RECEIPT_DAYS_AGO)]
    for quantity, days_ago in zip(sale_quantities, SALE_DAYS_AGO):
        plan.append(("sale", -quantity, days_ago))
    return plan


def seed() -> dict:
    db = SessionLocal()
    result = {"suppliers_created": [], "products_created": [], "skipped_suppliers": [], "skipped_products": []}
    try:
        supplier_by_name: dict[str, Supplier] = {}
        for payload in SUPPLIERS:
            existing = db.query(Supplier).filter(Supplier.name == payload["name"]).first()
            if existing:
                supplier_by_name[payload["name"]] = existing
                result["skipped_suppliers"].append(payload["name"])
                continue
            supplier = Supplier(
                name=payload["name"],
                supplier_code=payload["supplier_code"],
                contact_email=payload["contact_email"],
                payment_terms_days=payload["payment_terms_days"],
                lead_time_days=payload["lead_time_days"],
                is_active=True,
            )
            db.add(supplier)
            db.flush()
            supplier_by_name[payload["name"]] = supplier
            result["suppliers_created"].append(payload["name"])
        db.commit()

        now = datetime.utcnow()
        for (name, category, unit_price, cost_price, uom, reorder_point, reorder_quantity,
             supplier_name, final_available, daily_rate, trend) in PRODUCTS:
            existing = db.query(Product).filter(Product.name == name).first()
            if existing:
                result["skipped_products"].append(name)
                continue

            supplier = supplier_by_name[supplier_name]
            sku = generate_sku(category, db)
            product = Product(
                sku=sku,
                name=name,
                category=category,
                unit_price=unit_price,
                cost_price=cost_price,
                unit_of_measure=uom,
                reorder_point=reorder_point,
                reorder_quantity=reorder_quantity,
                supplier_id=supplier.id,
            )
            db.add(product)
            db.flush()
            upsert_stock_level(db, product.id)

            for movement_type, quantity, days_ago in build_movement_plan(final_available, daily_rate, trend):
                apply_stock_movement(
                    db,
                    product,
                    MovementType(movement_type),
                    quantity,
                    recorded_by="Demo Seeder",
                    reference_number="DEMO-SEED",
                    notes="Phase 5 demo inventory seed",
                )
            db.flush()

            # Backdate the movements we just inserted so they reflect a realistic history window.
            from app.models import StockMovement
            recent_movements = (
                db.query(StockMovement)
                .filter(StockMovement.product_id == product.id, StockMovement.reference_number == "DEMO-SEED")
                .order_by(StockMovement.id.asc())
                .all()
            )
            plan = build_movement_plan(final_available, daily_rate, trend)
            for movement, (_, _, days_ago) in zip(recent_movements, plan):
                movement.recorded_at = now - timedelta(days=days_ago)

            db.commit()
            result["products_created"].append({"name": name, "sku": sku, "final_available": final_available, "reorder_point": reorder_point})

        return result
    finally:
        db.close()


if __name__ == "__main__":
    import json

    outcome = seed()
    print(json.dumps(outcome, indent=2, default=str))
