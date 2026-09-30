"""Extended API tests covering auth, security, error paths, role guards, and edge-cases."""
from datetime import date, timedelta

import pytest

from app.security import create_access_token, decode_access_token, hash_password, verify_password


# ---------------------------------------------------------------------------
# Auth router tests
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_success(self, client):
        payload = {
            "email": "newuser@test.com",
            "password": "SecurePass@1",
            "full_name": "New User",
            "role": "staff",
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "staff"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_duplicate_email(self, client, seeded_user):
        payload = {
            "email": seeded_user.email,
            "password": "SecurePass@1",
            "full_name": "Dup",
            "role": "staff",
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        payload = {
            "email": "shortpw@test.com",
            "password": "abc",
            "full_name": "Test",
            "role": "staff",
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        payload = {
            "email": "not-an-email",
            "password": "ValidPass@1",
            "full_name": "Test",
            "role": "staff",
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, seeded_user):
        resp = client.post(
            "/api/v1/auth/login",
            data=f"username={seeded_user.email}&password=Password@123",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"

    def test_login_wrong_password(self, client, seeded_user):
        resp = client.post(
            "/api/v1/auth/login",
            data=f"username={seeded_user.email}&password=WrongPassword",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            data="username=nobody@nowhere.com&password=AnyPass@1",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_me_endpoint(self, client, auth_headers, seeded_user):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == seeded_user.email

    def test_me_no_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401

    def test_expired_token_rejected(self, client, db_session):
        token = create_access_token("9999", expires_delta=timedelta(seconds=-1))
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Security unit tests
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_password_hash_and_verify(self):
        pw = "TestPassword@123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)

    def test_wrong_password_rejected(self):
        hashed = hash_password("Correct@123")
        assert not verify_password("Wrong@123", hashed)

    def test_token_roundtrip(self):
        token = create_access_token("42")
        payload = decode_access_token(token)
        assert payload["sub"] == "42"

    def test_tampered_token_rejected(self):
        import jwt
        token = create_access_token("1")
        parts = token.split(".")
        parts[1] = parts[1][:-2] + "ZZ"
        bad_token = ".".join(parts)
        with pytest.raises(Exception):
            decode_access_token(bad_token)


# ---------------------------------------------------------------------------
# Products – extended
# ---------------------------------------------------------------------------

class TestProducts:
    def test_get_product_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/products/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_product(self, client, auth_headers, seeded_product):
        resp = client.patch(
            f"/api/v1/products/{seeded_product['id']}",
            json={"name": "Updated Name", "reorder_point": 30},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        assert resp.json()["reorder_point"] == 30

    def test_delete_product(self, client, auth_headers, seeded_supplier):
        create_resp = client.post(
            "/api/v1/products",
            json={
                "name": "Delete Me",
                "category": "household",
                "unit_price": 10.0,
                "cost_price": 8.0,
                "supplier_id": seeded_supplier["id"],
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        pid = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/products/{pid}", headers=auth_headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "Product deleted"

        get_resp = client.get(f"/api/v1/products/{pid}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_nonexistent_product(self, client, auth_headers):
        resp = client.delete("/api/v1/products/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_create_product_invalid_supplier(self, client, auth_headers):
        resp = client.post(
            "/api/v1/products",
            json={
                "name": "Bad Supplier Product",
                "category": "grocery",
                "unit_price": 10.0,
                "cost_price": 8.0,
                "supplier_id": 99999,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_list_products_low_stock_filter(self, client, auth_headers, seeded_product):
        client.patch(
            f"/api/v1/products/{seeded_product['id']}/stock",
            json={"movement_type": "sale", "quantity": -9999},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/products?low_stock=true", headers=auth_headers)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert seeded_product["id"] in ids

    def test_product_sku_personal_care_prefix(self, client, auth_headers, seeded_supplier):
        resp = client.post(
            "/api/v1/products",
            json={
                "name": "Shampoo",
                "category": "personal_care",
                "unit_price": 150.0,
                "cost_price": 100.0,
                "supplier_id": seeded_supplier["id"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["sku"].startswith("SKU-PRC-")

    def test_product_sku_electronics_prefix(self, client, auth_headers, seeded_supplier):
        resp = client.post(
            "/api/v1/products",
            json={
                "name": "Laptop",
                "category": "electronics",
                "unit_price": 50000.0,
                "cost_price": 40000.0,
                "supplier_id": seeded_supplier["id"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["sku"].startswith("SKU-ELC-")


# ---------------------------------------------------------------------------
# Suppliers – extended
# ---------------------------------------------------------------------------

class TestSuppliers:
    def test_list_suppliers(self, client, auth_headers, seeded_supplier):
        resp = client.get("/api/v1/suppliers", headers=auth_headers)
        assert resp.status_code == 200
        codes = [s["supplier_code"] for s in resp.json()]
        assert seeded_supplier["supplier_code"] in codes

    def test_get_supplier_by_id(self, client, auth_headers, seeded_supplier):
        resp = client.get(f"/api/v1/suppliers/{seeded_supplier['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == seeded_supplier["id"]

    def test_get_supplier_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/suppliers/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_supplier(self, client, auth_headers, seeded_supplier):
        resp = client.patch(
            f"/api/v1/suppliers/{seeded_supplier['id']}",
            json={"name": "Renamed Supplier"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Supplier"

    def test_delete_supplier(self, client, auth_headers):
        create_resp = client.post(
            "/api/v1/suppliers",
            json={
                "name": "Temp Supplier",
                "supplier_code": "TEMP-DEL-001",
                "contact_email": "temp@test.com",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        sid = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/suppliers/{sid}", headers=auth_headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "Supplier deleted"

    def test_duplicate_supplier_code(self, client, auth_headers, seeded_supplier):
        resp = client.post(
            "/api/v1/suppliers",
            json={
                "name": "Dup Supplier",
                "supplier_code": seeded_supplier["supplier_code"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_catalog_empty_for_supplier_without_products(self, client, auth_headers):
        s_resp = client.post(
            "/api/v1/suppliers",
            json={"name": "Empty Supplier", "supplier_code": "EMP-CAT-001"},
            headers=auth_headers,
        )
        sid = s_resp.json()["id"]
        resp = client.get(f"/api/v1/suppliers/{sid}/catalog", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_catalog_not_found_supplier(self, client, auth_headers):
        resp = client.get("/api/v1/suppliers/99999/catalog", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Purchase Orders – extended
# ---------------------------------------------------------------------------

class TestOrders:
    def test_list_orders(self, client, auth_headers):
        resp = client.get("/api/v1/orders", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_order_by_id(self, client, auth_headers, seeded_supplier, seeded_product):
        create_resp = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": seeded_supplier["id"],
                "order_date": date.today().isoformat(),
                "items": [{"product_id": seeded_product["id"], "quantity_ordered": 5, "unit_cost": 100.0}],
            },
            headers=auth_headers,
        )
        oid = create_resp.json()["id"]
        resp = client.get(f"/api/v1/orders/{oid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == oid

    def test_get_order_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/orders/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_create_po_invalid_supplier(self, client, auth_headers, seeded_product):
        resp = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": 99999,
                "order_date": date.today().isoformat(),
                "items": [{"product_id": seeded_product["id"], "quantity_ordered": 1, "unit_cost": 10.0}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_create_po_invalid_product(self, client, auth_headers, seeded_supplier):
        resp = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": seeded_supplier["id"],
                "order_date": date.today().isoformat(),
                "items": [{"product_id": 99999, "quantity_ordered": 1, "unit_cost": 10.0}],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_receive_draft_po_rejected(self, client, auth_headers, seeded_supplier, seeded_product):
        po_resp = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": seeded_supplier["id"],
                "order_date": date.today().isoformat(),
                "items": [{"product_id": seeded_product["id"], "quantity_ordered": 1, "unit_cost": 10.0}],
            },
            headers=auth_headers,
        )
        po_id = po_resp.json()["id"]
        resp = client.patch(f"/api/v1/orders/{po_id}/receive", headers=auth_headers)
        assert resp.status_code == 409

    def test_delete_order(self, client, auth_headers, seeded_supplier, seeded_product):
        po_resp = client.post(
            "/api/v1/orders",
            json={
                "supplier_id": seeded_supplier["id"],
                "order_date": date.today().isoformat(),
                "items": [{"product_id": seeded_product["id"], "quantity_ordered": 1, "unit_cost": 10.0}],
            },
            headers=auth_headers,
        )
        po_id = po_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/orders/{po_id}", headers=auth_headers)
        assert del_resp.status_code == 200

    def test_filter_orders_by_status(self, client, auth_headers, seeded_supplier, seeded_product):
        client.post(
            "/api/v1/orders",
            json={
                "supplier_id": seeded_supplier["id"],
                "order_date": date.today().isoformat(),
                "items": [{"product_id": seeded_product["id"], "quantity_ordered": 1, "unit_cost": 1.0}],
            },
            headers=auth_headers,
        )
        resp = client.get("/api/v1/orders?status=draft", headers=auth_headers)
        assert resp.status_code == 200
        for o in resp.json():
            assert o["status"] == "draft"


# ---------------------------------------------------------------------------
# Stock alerts
# ---------------------------------------------------------------------------

class TestStockAlerts:
    def test_low_alerts_empty(self, client, auth_headers):
        resp = client.get("/api/v1/stock/low-alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_out_of_stock_alert_type(self, client, auth_headers, seeded_product):
        client.patch(
            f"/api/v1/products/{seeded_product['id']}/stock",
            json={"movement_type": "sale", "quantity": -99999},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/stock/low-alerts", headers=auth_headers)
        assert resp.status_code == 200
        alerts = [a for a in resp.json() if a["id"] == seeded_product["id"]]
        assert len(alerts) >= 1
        assert alerts[0]["alert_type"] == "out_of_stock"

    def test_stock_movement_not_found(self, client, auth_headers):
        resp = client.patch(
            "/api/v1/products/99999/stock",
            json={"movement_type": "receipt", "quantity": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_dashboard_field_types(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["total_products"], int)
        assert isinstance(data["low_stock_count"], int)
        assert isinstance(data["out_of_stock_count"], int)
        assert isinstance(data["open_po_count"], int)
        assert isinstance(data["total_stock_value"], float)

    def test_dashboard_values_non_negative(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard", headers=auth_headers)
        data = resp.json()
        for field in ["total_products", "low_stock_count", "out_of_stock_count", "open_po_count"]:
            assert data[field] >= 0
        assert data["total_stock_value"] >= 0.0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["poc_id"] == "POC-07"


# ---------------------------------------------------------------------------
# Role authorization guards
# ---------------------------------------------------------------------------

class TestRoleGuards:
    def test_staff_cannot_access_dashboard(self, client, db_session):
        from app.models import User, UserRole
        from app.security import hash_password
        from fastapi.testclient import TestClient
        from app.database import get_db
        from app.main import app

        staff = User(
            email="staffguard@test.com",
            hashed_password=hash_password("Pass@1234"),
            full_name="Staff User",
            role=UserRole.staff,
            is_active=True,
        )
        db_session.add(staff)
        db_session.commit()

        def override():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override
        with TestClient(app) as tc:
            login_resp = tc.post(
                "/api/v1/auth/login",
                data="username=staffguard@test.com&password=Pass@1234",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token = login_resp.json()["access_token"]
            dash_resp = tc.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
        app.dependency_overrides.clear()

        assert dash_resp.status_code == 403
