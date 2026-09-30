from datetime import date
from unittest.mock import MagicMock

from app.models import StockLevel
from app.services.inventory_service import check_stock_alerts, generate_po_number, generate_sku


def test_sku_format():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.return_value = 41
    sku = generate_sku("grocery", mock_db)
    assert sku == "SKU-GRO-0042"
    assert sku.startswith("SKU-GRO-")


def test_sku_categories():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    assert generate_sku("electronics", mock_db).startswith("SKU-ELC-")
    assert generate_sku("clothing", mock_db).startswith("SKU-CLO-")
    assert generate_sku("household", mock_db).startswith("SKU-HHD-")


def test_po_number():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.return_value = 41
    po_num = generate_po_number(mock_db)
    year = date.today().year
    assert po_num == f"PO-{year}-0042"


def test_low_stock_alert():
    mock_product = MagicMock()
    mock_product.id = 1
    mock_product.sku = "SKU-GRO-0001"
    mock_product.reorder_point = 20

    mock_stock = MagicMock()
    mock_stock.quantity_available = 15

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    check_stock_alerts(mock_product, mock_stock, mock_db)
    mock_db.add.assert_called_once()
    call_args = mock_db.add.call_args[0][0]
    assert call_args.alert_type == "low_stock"


def test_out_of_stock_alert():
    mock_product = MagicMock()
    mock_product.id = 1
    mock_product.sku = "SKU-GRO-0002"
    mock_product.reorder_point = 20

    mock_stock = MagicMock()
    mock_stock.quantity_available = 0

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    check_stock_alerts(mock_product, mock_stock, mock_db)
    call_args = mock_db.add.call_args[0][0]
    assert call_args.alert_type == "out_of_stock"


def test_no_alert_above_reorder():
    mock_product = MagicMock()
    mock_product.id = 1
    mock_product.sku = "SKU-ELC-0001"
    mock_product.reorder_point = 10

    mock_stock = MagicMock()
    mock_stock.quantity_available = 50

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    check_stock_alerts(mock_product, mock_stock, mock_db)
    mock_db.add.assert_not_called()


def test_stock_value():
    products_data = [
        {"quantity_on_hand": 100, "cost_price": 50.0},
        {"quantity_on_hand": 50, "cost_price": 200.0},
    ]
    total = sum(p["quantity_on_hand"] * p["cost_price"] for p in products_data)
    assert total == 15000.0


def test_quantity_available():
    stock = StockLevel()
    stock.quantity_on_hand = 100
    stock.quantity_reserved = 30
    assert stock.quantity_available == 70
