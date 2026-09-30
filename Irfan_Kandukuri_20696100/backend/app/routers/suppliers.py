from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models import Product, Supplier, UserRole
from app.schemas import MessageResponse, SupplierCatalogItem, SupplierCreate, SupplierRead, SupplierUpdate


router = APIRouter()
SUPPLIER_NOT_FOUND = "Supplier not found"


@router.get("", response_model=list[SupplierRead])
def list_suppliers(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Supplier).order_by(Supplier.name.asc()).all()


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager, UserRole.procurement])),
):
    existing = db.query(Supplier).filter(Supplier.supplier_code == payload.supplier_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Supplier code already exists")

    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierRead)
@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager, UserRole.procurement])),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", response_model=MessageResponse)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager])),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    db.delete(supplier)
    db.commit()
    return MessageResponse(message="Supplier deleted")


@router.get("/{supplier_id}/catalog", response_model=list[SupplierCatalogItem])
def supplier_catalog(
    supplier_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND)

    products = db.query(Product).filter(Product.supplier_id == supplier_id).all()
    return [
        SupplierCatalogItem(
            product_id=item.id,
            sku=item.sku,
            name=item.name,
            category=item.category,
            unit_cost=item.cost_price,
        )
        for item in products
    ]
