from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models import AlertType, Product, StockAlert, StockLevel, UserRole
from app.schemas import AlertRead, MessageResponse, StockUpdateRequest
from app.services import apply_stock_movement


router = APIRouter()


@router.patch("/products/{product_id}", response_model=MessageResponse)
def update_stock(
    product_id: int,
    payload: StockUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles([UserRole.manager, UserRole.staff, UserRole.analyst])),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    apply_stock_movement(
        db=db,
        product=product,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reference_number=payload.reference_number,
        notes=payload.notes,
        recorded_by=user.full_name,
    )
    db.commit()
    return MessageResponse(message="Stock updated")


@router.get("/low-alerts", response_model=list[AlertRead])
def low_alerts(db: Session = Depends(get_db), _user=Depends(require_roles([UserRole.manager]))):
    products = db.query(Product).all()
    result: list[AlertRead] = []

    for product in products:
        stock = db.query(StockLevel).filter(StockLevel.product_id == product.id).first()
        available = stock.quantity_available if stock else 0
        if available > product.reorder_point:
            continue

        if available == 0:
            alert_type = AlertType.out_of_stock
            message = f"SKU {product.sku} is OUT OF STOCK."
        else:
            alert_type = AlertType.low_stock
            message = f"SKU {product.sku}: only {available} units left (reorder point: {product.reorder_point})."

        existing = (
            db.query(StockAlert)
            .filter(
                StockAlert.product_id == product.id,
                StockAlert.alert_type == alert_type,
                StockAlert.is_resolved.is_(False),
            )
            .order_by(StockAlert.triggered_at.desc())
            .first()
        )

        if existing is None:
            existing = StockAlert(
                product_id=product.id,
                alert_type=alert_type,
                message=message,
                is_resolved=False,
            )
            db.add(existing)
            db.flush()

        result.append(
            AlertRead(
                id=product.id,
                alert_id=existing.id,
                product_id=product.id,
                sku=product.sku,
                product_name=product.name,
                alert_type=alert_type,
                message=existing.message,
                is_resolved=existing.is_resolved,
                triggered_at=existing.triggered_at or datetime.now(timezone.utc),
            )
        )

    db.commit()

    priority = {AlertType.out_of_stock: 0, AlertType.low_stock: 1}
    return sorted(result, key=lambda item: (priority.get(item.alert_type, 99), item.triggered_at), reverse=False)
