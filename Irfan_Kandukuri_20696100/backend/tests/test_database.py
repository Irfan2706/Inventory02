from datetime import date

import pytest

from app.models import Category, POStatus, Product, PurchaseOrder, StockLevel, StockMovement


def test_sku_unique(db_session):
    p1 = Product(
        sku="SKU-GRO-9999",
        name="Test 1",
        category=Category.grocery,
        unit_price=100.0,
        cost_price=80.0,
    )
    db_session.add(p1)
    db_session.commit()

    with pytest.raises(Exception):
        p2 = Product(
            sku="SKU-GRO-9999",
            name="Test 2",
            category=Category.grocery,
            unit_price=100.0,
            cost_price=80.0,
        )
        db_session.add(p2)
        db_session.commit()


def test_movement_linked(db_session, seeded_product_db):
    movement = StockMovement(
        product_id=seeded_product_db.id,
        movement_type="receipt",
        quantity=50,
        recorded_by="Kiran",
    )
    db_session.add(movement)
    db_session.commit()

    assert movement.id is not None and movement.product_id == seeded_product_db.id


def test_po_unique(db_session, seeded_supplier_db):
    po1 = PurchaseOrder(
        po_number="PO-2026-9999",
        supplier_id=seeded_supplier_db.id,
        status=POStatus.draft,
        order_date=date.today(),
    )
    db_session.add(po1)
    db_session.commit()

    with pytest.raises(Exception):
        po2 = PurchaseOrder(
            po_number="PO-2026-9999",
            supplier_id=seeded_supplier_db.id,
            status=POStatus.draft,
            order_date=date.today(),
        )
        db_session.add(po2)
        db_session.commit()


def test_stock_level_one_to_one(db_session, seeded_product_db):
    with pytest.raises(Exception):
        s2 = StockLevel(product_id=seeded_product_db.id, quantity_on_hand=50)
        db_session.add(s2)
        db_session.commit()
