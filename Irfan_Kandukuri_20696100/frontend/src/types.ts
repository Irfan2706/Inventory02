export type Role = "admin" | "manager" | "analyst" | "procurement" | "staff";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
};

export type Supplier = {
  id: number;
  name: string;
  supplier_code: string;
  contact_email?: string | null;
  payment_terms_days: number;
  lead_time_days: number;
  is_active: boolean;
};

export type Product = {
  id: number;
  sku: string;
  name: string;
  category: string;
  unit_price: number;
  cost_price: number;
  unit_of_measure: string;
  reorder_point: number;
  reorder_quantity: number;
  supplier_id?: number | null;
};

export type StockLevel = {
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
};

export type StockMovement = {
  id: number;
  movement_type: string;
  quantity: number;
  reference_number?: string | null;
  notes?: string | null;
  recorded_at: string;
  recorded_by: string;
};

export type ProductDetail = Product & {
  stock_level?: StockLevel | null;
  movements: StockMovement[];
};

export type POItem = {
  id?: number;
  product_id: number;
  quantity_ordered: number;
  unit_cost: number;
  quantity_received?: number | null;
};

export type PurchaseOrder = {
  id: number;
  po_number: string;
  supplier_id: number;
  status: "draft" | "submitted" | "acknowledged" | "received" | "cancelled";
  total_amount: number;
  order_date: string;
  expected_delivery?: string | null;
  received_date?: string | null;
  items: POItem[];
};

export type StockAlert = {
  id: number;
  product_id: number;
  sku: string;
  product_name: string;
  alert_type: "low_stock" | "out_of_stock";
  message: string;
  is_resolved: boolean;
  triggered_at: string;
};

export type DashboardSummary = {
  total_products: number;
  low_stock_count: number;
  out_of_stock_count: number;
  open_po_count: number;
  total_stock_value: number;
};

export type RagSource = {
  source: string;
  chunk_index?: number | null;
  section?: string | null;
  content: string;
};

export type RagQueryResponse = {
  answer: string;
  sources: RagSource[];
};

export type AgentQueryResponse = {
  answer: string;
  tools_used: string[];
  reasoning: string;
};

export type MCPChatResponse = {
  output: string;
  session_id: string;
  tools_used: string[];
  tool_traces: { tool: string; result: unknown }[];
  history: { role: string; content: string; timestamp?: string }[];
};

export type DemandForecast = {
  avg_daily_demand: number;
  demand_trend: string;
  days_of_stock_remaining: number;
  stockout_risk: string;
  forecast_notes: string;
};

export type ReorderRecommendation = {
  reorder_required: boolean;
  recommended_quantity: number;
  urgency: string;
  reason: string;
};

export type SupplierQuote = {
  supplier_id?: number | null;
  quoted_unit_cost: number;
  total_order_cost: number;
  estimated_lead_time_days: number;
  quote_notes: string;
};

export type MultiAgentAnalysisResponse = {
  product_id: number;
  demand_forecast: DemandForecast;
  reorder_recommendation: ReorderRecommendation;
  supplier_quote: SupplierQuote;
  audit_report: string;
  analysis_status: string;
  errors: string[];
  messages: string[];
};
