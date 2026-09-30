from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AlertType, Category, MovementType, POStatus, UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    role: UserRole = UserRole.staff


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


class SupplierBase(BaseModel):
    name: str
    supplier_code: str
    contact_email: Optional[EmailStr] = None
    payment_terms_days: int = 30
    lead_time_days: int = 7
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    payment_terms_days: Optional[int] = None
    lead_time_days: Optional[int] = None
    is_active: Optional[bool] = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProductBase(BaseModel):
    name: str
    category: Category
    unit_price: float = Field(gt=0)
    cost_price: float = Field(gt=0)
    unit_of_measure: str = "pieces"
    reorder_point: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, gt=0)
    supplier_id: Optional[int] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[Category] = None
    unit_price: Optional[float] = Field(default=None, gt=0)
    cost_price: Optional[float] = Field(default=None, gt=0)
    unit_of_measure: Optional[str] = None
    reorder_point: Optional[int] = Field(default=None, ge=0)
    reorder_quantity: Optional[int] = Field(default=None, gt=0)
    supplier_id: Optional[int] = None


class StockLevelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_type: MovementType
    quantity: int
    reference_number: Optional[str]
    notes: Optional[str]
    recorded_at: datetime
    recorded_by: str


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: Category
    unit_price: float
    cost_price: float
    unit_of_measure: str
    reorder_point: int
    reorder_quantity: int
    supplier_id: Optional[int]


class ProductDetail(ProductRead):
    stock_level: Optional[StockLevelRead] = None
    movements: list[StockMovementRead] = []


class StockUpdateRequest(BaseModel):
    movement_type: MovementType
    quantity: int
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class POItemCreate(BaseModel):
    product_id: int
    quantity_ordered: int = Field(gt=0)
    unit_cost: float = Field(gt=0)


class POItemUpdate(BaseModel):
    quantity_ordered: Optional[int] = Field(default=None, gt=0)
    unit_cost: Optional[float] = Field(default=None, gt=0)
    quantity_received: Optional[int] = Field(default=None, ge=0)


class POItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity_ordered: int
    unit_cost: float
    quantity_received: Optional[int]


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    order_date: date
    expected_delivery: Optional[date] = None
    status: POStatus = POStatus.draft
    items: list[POItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    order_date: Optional[date] = None
    expected_delivery: Optional[date] = None
    status: Optional[POStatus] = None


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_number: str
    supplier_id: int
    status: POStatus
    total_amount: float
    order_date: date
    expected_delivery: Optional[date]
    received_date: Optional[date]
    items: list[POItemRead] = []


class AlertRead(BaseModel):
    id: int
    alert_id: Optional[int] = None
    product_id: int
    sku: str
    product_name: str
    alert_type: AlertType
    message: str
    is_resolved: bool
    triggered_at: datetime


class SupplierCatalogItem(BaseModel):
    product_id: int
    sku: str
    name: str
    category: Category
    unit_cost: float


class DashboardSummary(BaseModel):
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    open_po_count: int
    total_stock_value: float


class MessageResponse(BaseModel):
    message: str
