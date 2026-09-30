from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, require_roles
from app.database import get_db
from app.logging_config import get_logger
from app.models import POItem, POStatus, Product, PurchaseOrder, Supplier, UserRole
from app.schemas import MessageResponse, PurchaseOrderCreate, PurchaseOrderRead, PurchaseOrderUpdate
from app.services import generate_po_number, recalculate_po_total, receive_purchase_order


router = APIRouter()
PURCHASE_ORDER_NOT_FOUND = "Purchase order not found"
SUPPLIER_NOT_FOUND = "Supplier not found"
logger = get_logger("orders")


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles([UserRole.manager, UserRole.procurement])),
):
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    po = PurchaseOrder(
        po_number=generate_po_number(db),
        supplier_id=payload.supplier_id,
        status=POStatus.draft,
        order_date=payload.order_date,
        expected_delivery=payload.expected_delivery,
    )
    db.add(po)
    db.flush()

    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item.product_id} not found")
        db.add(POItem(po_id=po.id, **item.model_dump()))

    db.flush()
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).first()
    recalculate_po_total(po)

    db.commit()
    db.refresh(po)

    logger.info(
        "po_created",
        poc_id=settings.poc_id,
        phase="P1",
        po_number=po.po_number,
        supplier_id=po.supplier_id,
        total_amount=po.total_amount,
        user_id=user.id,
    )

    return po


@router.get("", response_model=list[PurchaseOrderRead])
def list_orders(
    status_filter: POStatus | None = Query(default=None, alias="status"),
    supplier: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(PurchaseOrder)
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    if supplier:
        query = query.filter(PurchaseOrder.supplier_id == supplier)
    return query.order_by(PurchaseOrder.created_at.desc()).all()


@router.get("/{order_id}", response_model=PurchaseOrderRead)
def get_order(order_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PURCHASE_ORDER_NOT_FOUND)
    return po


@router.patch("/{order_id}", response_model=PurchaseOrderRead)
def update_order(
    order_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager, UserRole.procurement])),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PURCHASE_ORDER_NOT_FOUND)

    update_data = payload.model_dump(exclude_unset=True)
    if "supplier_id" in update_data:
        supplier = db.query(Supplier).filter(Supplier.id == update_data["supplier_id"]).first()
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    for key, value in update_data.items():
        setattr(po, key, value)

    db.commit()
    db.refresh(po)
    return po


@router.delete("/{order_id}", response_model=MessageResponse)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager])),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PURCHASE_ORDER_NOT_FOUND)

    db.delete(po)
    db.commit()
    return MessageResponse(message="Purchase order deleted")


@router.patch("/{order_id}/receive", response_model=PurchaseOrderRead)
def receive_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles([UserRole.manager, UserRole.staff])),
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if po is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PURCHASE_ORDER_NOT_FOUND)

    po = receive_purchase_order(po, db, recorded_by=user.full_name)
    db.commit()
    db.refresh(po)
    return po
