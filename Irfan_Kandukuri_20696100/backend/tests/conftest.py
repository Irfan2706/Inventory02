from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base, get_db
from app.main import app
from app.models import Category, POStatus, Product, PurchaseOrder, StockLevel, Supplier, User, UserRole
from app.security import hash_password


TEST_DB_PATH = ROOT / "test_inventory.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except PermissionError:
            # On Windows, file handles may linger briefly after test teardown.
            pass


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_user(db_session):
    user = User(
        email="manager.test@poc07.com",
        hashed_password=hash_password("Password@123"),
        full_name="Manager Test",
        role=UserRole.manager,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client, seeded_user):
    payload = "username=manager.test@poc07.com&password=Password@123"
    response = client.post(
        "/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def seeded_supplier(client, auth_headers):
    payload = {
        "name": "Seeded Supplier",
        "supplier_code": "SUP-SEED-0001",
        "contact_email": "seeded@supplier.com",
        "payment_terms_days": 30,
        "lead_time_days": 7,
        "is_active": True,
    }
    response = client.post("/api/v1/suppliers", json=payload, headers=auth_headers)
    return response.json()


@pytest.fixture()
def seeded_product(client, auth_headers, seeded_supplier):
    payload = {
        "name": "Seeded Product",
        "category": "grocery",
        "unit_price": 300.0,
        "cost_price": 250.0,
        "unit_of_measure": "box",
        "reorder_point": 20,
        "reorder_quantity": 100,
        "supplier_id": seeded_supplier["id"],
    }
    response = client.post("/api/v1/products", json=payload, headers=auth_headers)
    return response.json()


@pytest.fixture()
def submitted_po(client, auth_headers, seeded_supplier, seeded_product):
    payload = {
        "supplier_id": seeded_supplier["id"],
        "order_date": date.today().isoformat(),
        "expected_delivery": date.today().isoformat(),
        "items": [
            {
                "product_id": seeded_product["id"],
                "quantity_ordered": 100,
                "unit_cost": 280.0,
            }
        ],
    }
    response = client.post("/api/v1/orders", json=payload, headers=auth_headers)
    po = response.json()
    client.patch(f"/api/v1/orders/{po['id']}", json={"status": POStatus.submitted.value}, headers=auth_headers)
    return po["id"]


@pytest.fixture()
def seeded_supplier_db(db_session):
    supplier = Supplier(
        name="DB Seed Supplier",
        supplier_code="SUP-DB-0001",
        contact_email="db@supplier.com",
        payment_terms_days=30,
        lead_time_days=7,
        is_active=True,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture()
def seeded_product_db(db_session, seeded_supplier_db):
    product = Product(
        sku="SKU-GRO-1000",
        name="DB Seed Product",
        category=Category.grocery,
        unit_price=100.0,
        cost_price=80.0,
        supplier_id=seeded_supplier_db.id,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    stock = StockLevel(product_id=product.id, quantity_on_hand=10, quantity_reserved=0)
    db_session.add(stock)
    db_session.commit()

    return product
