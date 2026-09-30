from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models import Product, StockLevel, StockMovement, Supplier, UserRole
from app.schemas import MessageResponse, ProductCreate, ProductDetail, ProductRead, ProductUpdate, StockUpdateRequest
from app.services import apply_stock_movement, generate_sku, upsert_stock_level


router = APIRouter()
PRODUCT_NOT_FOUND = "Product not found"
SUPPLIER_NOT_FOUND = "Supplier not found"


@router.get("", response_model=list[ProductRead])
def list_products(
    category: str | None = Query(default=None),
    low_stock: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(Product).options(joinedload(Product.stock_level))
    if category:
        query = query.filter(Product.category == category)
    products = query.all()

    if low_stock:
        return [
            p for p in products
            if (p.stock_level.quantity_available if p.stock_level else 0) <= p.reorder_point
        ]

    return products


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager, UserRole.procurement])),
):
    if payload.supplier_id is not None:
        supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    sku = generate_sku(payload.category.value, db)
    product = Product(sku=sku, **payload.model_dump())
    db.add(product)
    db.flush()
    upsert_stock_level(db, product.id)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)

    stock = db.query(StockLevel).filter(StockLevel.product_id == product.id).first()
    movements = (
        db.query(StockMovement)
        .filter(StockMovement.product_id == product.id)
        .order_by(StockMovement.recorded_at.desc())
        .limit(25)
        .all()
    )

    return ProductDetail(
        **ProductRead.model_validate(product).model_dump(),
        stock_level=stock,
        movements=movements,
    )


@router.put("/{product_id}", response_model=ProductRead)
@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager, UserRole.procurement])),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)

    update_data = payload.model_dump(exclude_unset=True)
    if "supplier_id" in update_data and update_data["supplier_id"] is not None:
        supplier = db.query(Supplier).filter(Supplier.id == update_data["supplier_id"]).first()
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager])),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)

    db.delete(product)
    db.commit()
    return MessageResponse(message="Product deleted")


@router.patch("/{product_id}/stock", response_model=MessageResponse)
def update_product_stock(
    product_id: int,
    payload: StockUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles([UserRole.manager, UserRole.staff, UserRole.analyst])),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)

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
