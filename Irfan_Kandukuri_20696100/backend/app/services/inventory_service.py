from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger
from app.models import (
    AlertType,
    CATEGORY_PREFIXES,
    POStatus,
    MovementType,
    Product,
    PurchaseOrder,
    StockAlert,
    StockLevel,
    StockMovement,
)


logger = get_logger("services")


def generate_sku(category: str, db: Session) -> str:
    prefix = CATEGORY_PREFIXES.get(category, "GEN")
    count = db.query(Product).filter(Product.sku.like(f"SKU-{prefix}-%")).count()
    return f"SKU-{prefix}-{count + 1:04d}"


def generate_po_number(db: Session) -> str:
    year = date.today().year
    count = db.query(PurchaseOrder).filter(PurchaseOrder.po_number.like(f"PO-{year}-%")).count()
    return f"PO-{year}-{count + 1:04d}"


def upsert_stock_level(db: Session, product_id: int) -> StockLevel:
    stock = db.query(StockLevel).filter(StockLevel.product_id == product_id).first()
    if stock is None:
        stock = StockLevel(product_id=product_id, quantity_on_hand=0, quantity_reserved=0)
        db.add(stock)
        db.flush()
    return stock


def check_stock_alerts(product: Product, stock: StockLevel, db: Session) -> None:
    available = stock.quantity_available
    existing_active = (
        db.query(StockAlert)
        .filter(StockAlert.product_id == product.id, StockAlert.is_resolved.is_(False))
        .all()
    )

    if available == 0:
        alert_type = AlertType.out_of_stock
        message = f"SKU {product.sku} is OUT OF STOCK."
    elif available <= product.reorder_point:
        alert_type = AlertType.low_stock
        message = f"SKU {product.sku}: only {available} units left (reorder point: {product.reorder_point})."
    else:
        for alert in existing_active:
            alert.is_resolved = True
        return

    if not any(alert.alert_type == alert_type for alert in existing_active):
        db.add(
            StockAlert(
                product_id=product.id,
                alert_type=alert_type,
                message=message,
                is_resolved=False,
            )
        )
        logger.info(
            "low_stock_alert",
            poc_id=settings.poc_id,
            phase="P1",
            product_sku=product.sku,
            quantity_available=available,
            reorder_point=product.reorder_point,
        )


def apply_stock_movement(
    db: Session,
    product: Product,
    movement_type: MovementType,
    quantity: int,
    recorded_by: str,
    reference_number: str | None = None,
    notes: str | None = None,
) -> StockLevel:
    stock = upsert_stock_level(db, product.id)
    stock.quantity_on_hand += quantity

    if stock.quantity_on_hand < 0:
        # Clamp to zero so large sale adjustments still produce movement and stock alerts.
        stock.quantity_on_hand = 0

    db.add(
        StockMovement(
            product_id=product.id,
            movement_type=movement_type,
            quantity=quantity,
            reference_number=reference_number,
            notes=notes,
            recorded_by=recorded_by,
        )
    )

    check_stock_alerts(product, stock, db)

    logger.info(
        "stock_updated",
        poc_id=settings.poc_id,
        phase="P1",
        product_sku=product.sku,
        movement_type=movement_type.value,
        quantity=quantity,
        new_quantity_on_hand=stock.quantity_on_hand,
    )

    return stock


def recalculate_po_total(po: PurchaseOrder) -> None:
    po.total_amount = sum(item.quantity_ordered * item.unit_cost for item in po.items)


def receive_purchase_order(po: PurchaseOrder, db: Session, recorded_by: str) -> PurchaseOrder:
    if po.status not in {POStatus.submitted, POStatus.acknowledged}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted or acknowledged POs can be received",
        )

    po.status = POStatus.received
    po.received_date = date.today()

    for item in po.items:
        qty = item.quantity_received if item.quantity_received is not None else item.quantity_ordered
        item.quantity_received = qty
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PO item product not found")

        apply_stock_movement(
            db=db,
            product=product,
            movement_type=MovementType.receipt,
            quantity=qty,
            recorded_by=recorded_by,
            reference_number=po.po_number,
            notes=f"Received from PO {po.po_number}",
        )

        (
            db.query(StockAlert)
            .filter(StockAlert.product_id == item.product_id, StockAlert.is_resolved.is_(False))
            .update({"is_resolved": True})
        )

    logger.info(
        "po_received",
        poc_id=settings.poc_id,
        phase="P1",
        po_number=po.po_number,
        supplier_id=po.supplier_id,
    )

    return po


def dashboard_summary(db: Session) -> dict:
    total_products = db.query(func.count(Product.id)).scalar() or 0

    stocks = db.query(Product, StockLevel).outerjoin(StockLevel, Product.id == StockLevel.product_id).all()
    low_stock_count = 0
    out_of_stock_count = 0
    total_stock_value = 0.0

    for product, stock in stocks:
        on_hand = stock.quantity_on_hand if stock else 0
        reserved = stock.quantity_reserved if stock else 0
        available = max(0, on_hand - reserved)
        if available == 0:
            out_of_stock_count += 1
        if available <= product.reorder_point:
            low_stock_count += 1
        total_stock_value += on_hand * product.cost_price

    open_po_count = (
        db.query(func.count(PurchaseOrder.id))
        .filter(PurchaseOrder.status.in_([POStatus.draft, POStatus.submitted, POStatus.acknowledged]))
        .scalar()
        or 0
    )

    return {
        "total_products": int(total_products),
        "low_stock_count": int(low_stock_count),
        "out_of_stock_count": int(out_of_stock_count),
        "open_po_count": int(open_po_count),
        "total_stock_value": round(float(total_stock_value), 2),
    }
