def test_create_product(client, auth_headers, seeded_supplier):
    payload = {
        "name": "Basmati Rice 5kg",
        "category": "grocery",
        "unit_price": 350.0,
        "cost_price": 280.0,
        "unit_of_measure": "box",
        "reorder_point": 20,
        "reorder_quantity": 100,
        "supplier_id": seeded_supplier["id"],
    }
    response = client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["sku"].startswith("SKU-GRO-")


def test_stock_update_alert(client, auth_headers, seeded_product):
    payload = {
        "movement_type": "sale",
        "quantity": -1000,
        "reference_number": "SALE-001",
        "notes": "Bulk sale",
    }
    response = client.patch(
        f"/api/v1/products/{seeded_product['id']}/stock",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200

    alerts_response = client.get("/api/v1/stock/low-alerts", headers=auth_headers)
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert any(p["id"] == seeded_product["id"] for p in alerts)


def test_create_po(client, auth_headers, seeded_supplier, seeded_product):
    payload = {
        "supplier_id": seeded_supplier["id"],
        "order_date": "2026-06-18",
        "expected_delivery": "2026-06-25",
        "items": [{"product_id": seeded_product["id"], "quantity_ordered": 100, "unit_cost": 280.0}],
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert "po_number" in data
    assert data["po_number"].startswith("PO-")
    assert data["status"] == "draft"


def test_receive_po_updates_stock(client, auth_headers, submitted_po, seeded_product):
    initial_stock = client.get(
        f"/api/v1/products/{seeded_product['id']}",
        headers=auth_headers,
    ).json().get("stock_level", {})

    response = client.patch(f"/api/v1/orders/{submitted_po}/receive", headers=auth_headers)
    assert response.status_code == 200

    updated = client.get(
        f"/api/v1/products/{seeded_product['id']}",
        headers=auth_headers,
    ).json()
    new_stock = updated.get("stock_level", {})
    assert new_stock.get("quantity_on_hand", 0) > initial_stock.get("quantity_on_hand", 0)


def test_low_alerts(client, auth_headers):
    response = client.get("/api/v1/stock/low-alerts", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_supplier_catalog(client, auth_headers, seeded_supplier):
    response = client.get(f"/api/v1/suppliers/{seeded_supplier['id']}/catalog", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_filter_by_category(client, auth_headers):
    response = client.get("/api/v1/products?category=grocery", headers=auth_headers)
    assert response.status_code == 200
    for product in response.json():
        assert product["category"] == "grocery"


def test_dashboard(client, auth_headers):
    response = client.get("/api/v1/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    for field in [
        "total_products",
        "low_stock_count",
        "out_of_stock_count",
        "open_po_count",
        "total_stock_value",
    ]:
        assert field in data
