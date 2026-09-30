# Inventory Management & Procurement Operations Manual
## POC-07 — Retail Inventory Reference Guide

### Section 1: Introduction to Inventory Management

Inventory management is the process of ordering, storing, and using a company's inventory — raw materials, components, and finished products. Effective inventory management ensures products are available when customers need them while minimizing carrying costs and avoiding overstock situations.

This system manages four main activities: product catalog management, stock level tracking, purchase order management, and stock movement recording. All inventory changes are recorded as movements for full auditability.

Operationally, every team should treat the manual as the source of truth during daily inventory reviews. Exceptions should be documented against the related SKU or PO number so the audit trail stays complete.

### Section 2: Product Catalog and SKU System

Every product has a unique SKU (Stock Keeping Unit) in the format SKU-{CATEGORY_PREFIX}-{NNNN}.

Category prefixes:
- GRO: Grocery products
- ELC: Electronics
- CLO: Clothing and apparel
- HHD: Household items
- PRC: Personal care products

Examples: SKU-GRO-0042 (Grocery item #42), SKU-ELC-0015 (Electronics item #15).

Each product has: unit_price (selling price in ₹), cost_price (purchase cost in ₹), unit_of_measure (pieces/kg/litre/box), reorder_point (trigger level for replenishment), and reorder_quantity (standard order size).

The SKU prefix is also used in reports and supplier communication, so the code must stay stable once a product is published. If a code is mistyped, staff should correct the catalog entry before the next replenishment cycle.

### Section 3: Stock Levels and Reorder Points

Every product has a StockLevel record tracking:
- quantity_on_hand: physical inventory count
- quantity_reserved: allocated to pending customer orders
- quantity_available: on_hand minus reserved (this is the working stock)

The reorder_point is the stock level at which a replenishment order should be initiated. Setting it correctly requires knowing: average daily demand × supplier lead time + safety stock.

Example: A product selling 10 units per day with a 5-day supplier lead time and 2 days safety stock needs a reorder point of (10 × 5) + (10 × 2) = 70 units.

The same method can be reused for seasonal demand by replacing the daily demand estimate with the current demand forecast. Reorder calculations should always be recorded alongside the supplier lead time and safety stock assumption.

### Section 4: Stock Alert System

The system automatically generates alerts based on stock conditions:

**Low Stock Alert:** Triggered when quantity_available ≤ reorder_point. This is a warning — action should be taken within 24-48 hours to raise a purchase order.

**Out of Stock Alert:** Triggered when quantity_available = 0. This is critical — immediate action required. Lost sales occur with every customer request while stock is zero.

**Reorder Suggested Alert:** The system may also suggest reorder quantities based on historical consumption patterns.

All alerts can be resolved once a purchase order is submitted. Resolved alerts remain in the audit log.

Low stock alerts should be reviewed before the end of the same business day, especially for grocery and personal care items. Duplicate alerts should be suppressed until the current alert is resolved.

### Section 5: Purchase Order (PO) Process

Purchase Orders are the formal mechanism for ordering from suppliers. The PO lifecycle:

1. **Draft:** Created by procurement officer, items added
2. **Submitted:** Sent to supplier (email or system notification)
3. **Acknowledged:** Supplier confirms receipt and delivery date
4. **Received:** Goods arrive, staff marks as received, stock updated automatically
5. **Cancelled:** PO cancelled before receipt

PO number format: PO-{YEAR}-{NNNN}, e.g., PO-2026-0042.

When a PO is marked as received, the system automatically:
- Creates StockMovement(receipt) records for each line item
- Updates quantity_on_hand for each product
- Resolves any low_stock/out_of_stock alerts for received products

If only part of a PO is received, staff should record the receipt quantities exactly as delivered and keep the PO open for the balance. This prevents mismatches between the supplier invoice and inventory quantities.

### Section 6: Supplier Management

Suppliers have the following key attributes:
- supplier_code: unique identifier (SUP-0001 format)
- lead_time_days: how many days from order to delivery
- payment_terms_days: net payment window (e.g., Net 30 = payment within 30 days)
- is_active: only active suppliers can receive new POs

Supplier selection criteria: price competitiveness, lead time, reliability, and payment terms. Always verify a supplier is active before raising a PO.

Inactive suppliers must not receive new orders until procurement confirms the account is reactivated. Supplier review should include escalation history and average delivery performance where available.

### Section 7: Stock Movement Recording

Every inventory change must be recorded as a StockMovement with a movement_type:

- **receipt:** Goods received from a PO (positive quantity)
- **sale:** Goods sold to a customer (negative quantity — use negative values)
- **adjustment:** Manual correction after physical count discrepancy
- **transfer:** Moved between warehouses
- **return:** Customer return or supplier return

The reference_number should link to the source document (PO number, sale order number, etc.). All movements are timestamped and attributed to a staff member.

Movement records should be created as close to the operational event as possible so the stock ledger remains accurate. Manual corrections should include a short note describing the reason for the change.

### Section 8: Inventory Valuation

Inventory is valued at cost price using the FIFO (First In, First Out) method. Total stock value = SUM(product.cost_price × stock_level.quantity_on_hand) across all products.

The dashboard shows total_stock_value to give management visibility into working capital tied up in inventory. Overstock (inventory far above reorder needs) increases carrying costs.

Valuation reports should be based on cost price rather than selling price so finance can compare inventory investment against actual cash tied up in stock. When a product has no stock on hand, its contribution to total value is zero.

### Section 9: Reorder Quantity Calculation

The Economic Order Quantity (EOQ) formula helps determine optimal reorder quantity:
EOQ = √(2 × annual_demand × ordering_cost / holding_cost_per_unit)

In practice, most retailers use a simpler rule: order enough to cover lead_time + safety stock period. Example: if a product sells 5 units/day, lead time is 7 days, and safety stock is 14 days: reorder quantity = (5 × 7) + (5 × 14) = 35 + 70 = 105 units.

EOQ is helpful for strategic planning, but operational teams usually prioritize lead-time coverage and service levels. The selected reorder quantity should also respect supplier minimum order quantities and storage constraints.

### Section 10: Procurement Officer Responsibilities

The Procurement Officer (Anita Singh) is responsible for:
1. Monitoring low_stock alerts daily
2. Reviewing supplier catalogs for best prices
3. Raising POs within 24 hours of a low_stock alert
4. Confirming supplier acknowledgement
5. Coordinating goods receipt with warehouse staff

PO approval: POs above ₹50,000 require Store Manager approval before submission.

Procurement officers should attach the approval note before submitting any high-value PO. If approval is delayed, the PO should remain in draft status until the store manager confirms it.

### Section 11: Stock Count and Reconciliation

Physical stock counts should be performed:
- **Cycle count:** Count a subset of products daily/weekly (high-value items weekly)
- **Full count:** Count all products quarterly

When a discrepancy is found: record a StockMovement(adjustment) with the difference. If positive: system had less than physical count (count was understated). If negative: system had more than physical count (shrinkage, theft, or damage).

Cycle counts should focus on high-value or fast-moving products first because those lines create the greatest risk if the ledger drifts. Reconciliation results should be reviewed by the store manager before the next receiving cycle.

### Section 12: Category Management

Each category has different characteristics:
- **Grocery:** Short shelf life, high velocity, tight reorder management needed
- **Electronics:** High unit cost, lower velocity, longer lead times typical
- **Clothing:** Seasonal demand patterns, size/variant management important
- **Household:** Moderate velocity, predictable demand
- **Personal Care:** High velocity, brand loyalty, competitive market

Category strategy affects both stock policy and replenishment frequency. A fast-moving grocery item may need tighter safety stock than an electronic accessory with a longer selling cycle.

### Section 13: Reporting and Analytics

Key inventory reports:
- **Slow-moving stock:** Products with no movement in 30+ days
- **Stock turn ratio:** Cost of goods sold / average inventory value (higher = better)
- **Fill rate:** Percentage of orders fulfilled without stockout
- **Days on hand:** quantity_on_hand / average daily sales

Store Manager reviews these weekly. Raj Patel (Inventory Analyst) prepares monthly trend reports.

Reports should highlight both the operational signal and the likely action, such as reorder, discount, or review for shrinkage. Trend reporting becomes more useful when stock turn and fill rate are tracked together.

### Section 14: System Integration

The inventory system integrates with:
- Point of Sale (POS): sales movements recorded automatically
- Supplier portal: PO submission and acknowledgement
- Finance: PO amounts flow to accounts payable

When integration is not available, manual StockMovement records must be entered.

Manual entries should preserve the same reference number structure used by integrated systems so downstream reconciliation remains consistent. Any gap in automation should be temporary and tracked until the integration is restored.

### Section 15: Troubleshooting

**Problem: Stock level shows negative**
Cause: Sale recorded before receipt, or data entry error.
Fix: Record a positive StockMovement(adjustment) to correct. Investigate the root cause.

**Problem: Duplicate low_stock alerts**
Cause: Multiple triggers before first alert was resolved.
Fix: The system should check for existing unresolved alert before creating a new one.

**Problem: PO received but stock not updated**
Cause: PATCH /orders/{id}/receive not called, or failed silently.
Fix: Check API logs, verify PO status is "received", manually trigger receipt if needed.

**Problem: SKU not found by supplier**
Cause: Product registered in system but not in supplier catalog.
Fix: Add product to supplier's catalog, verify supplier_id on product record.

If the issue persists after catalog updates, the team should verify the SKU prefix, supplier status, and product master data before escalating. Troubleshooting should end with a corrective stock movement only after the root cause is documented.
