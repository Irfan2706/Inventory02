import { FormEvent, useEffect, useState } from "react";

import { api, apiError } from "../services/api";
import type { Product, PurchaseOrder, Supplier } from "../types";

export function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    supplier_id: "",
    order_date: new Date().toISOString().slice(0, 10),
    expected_delivery: "",
    product_id: "",
    quantity_ordered: 1,
    unit_cost: 0,
  });

  const load = async () => {
    try {
      const [oRes, sRes, pRes] = await Promise.all([
        api.get<PurchaseOrder[]>("/orders"),
        api.get<Supplier[]>("/suppliers"),
        api.get<Product[]>("/products"),
      ]);
      setOrders(oRes.data);
      setSuppliers(sRes.data);
      setProducts(pRes.data);
    } catch (err) {
      setError(apiError(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.supplier_id || !form.product_id) {
      setError("Supplier and product are required");
      return;
    }

    try {
      await api.post("/orders", {
        supplier_id: Number(form.supplier_id),
        order_date: form.order_date,
        expected_delivery: form.expected_delivery || null,
        status: "submitted",
        items: [
          {
            product_id: Number(form.product_id),
            quantity_ordered: Number(form.quantity_ordered),
            unit_cost: Number(form.unit_cost),
          },
        ],
      });
      setForm((prev) => ({ ...prev, product_id: "", quantity_ordered: 1, unit_cost: 0 }));
      await load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const receiveOrder = async (id: number, status: string) => {
    try {
      if (status === "draft") {
        await api.patch(`/orders/${id}`, { status: "submitted" });
      }
      await api.patch(`/orders/${id}/receive`);
      await load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="font-heading text-2xl font-bold">Purchase Orders</h1>

      <section className="card">
        <h2 className="mb-3 font-heading text-lg font-semibold">Create Purchase Order</h2>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
          <select
            className="input"
            value={form.supplier_id}
            onChange={(e) => setForm((prev) => ({ ...prev, supplier_id: e.target.value }))}
            required
          >
            <option value="">Select supplier</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <select
            className="input"
            value={form.product_id}
            onChange={(e) => {
              const value = e.target.value;
              const product = products.find((p) => p.id === Number(value));
              setForm((prev) => ({
                ...prev,
                product_id: value,
                unit_cost: product?.cost_price ?? prev.unit_cost,
              }));
            }}
            required
          >
            <option value="">Select product</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.sku})
              </option>
            ))}
          </select>

          <input
            className="input"
            type="date"
            value={form.order_date}
            onChange={(e) => setForm((prev) => ({ ...prev, order_date: e.target.value }))}
            required
          />
          <input
            className="input"
            type="date"
            value={form.expected_delivery}
            onChange={(e) => setForm((prev) => ({ ...prev, expected_delivery: e.target.value }))}
          />

          <input
            className="input"
            type="number"
            min={1}
            value={form.quantity_ordered}
            onChange={(e) => setForm((prev) => ({ ...prev, quantity_ordered: Number(e.target.value) }))}
            required
          />
          <input
            className="input"
            type="number"
            min={0}
            step="0.01"
            value={form.unit_cost}
            onChange={(e) => setForm((prev) => ({ ...prev, unit_cost: Number(e.target.value) }))}
            required
          />

          <div className="md:col-span-2">
            <button className="btn-primary" type="submit">
              Create PO
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left">
                <th className="p-2">PO Number</th>
                <th className="p-2">Supplier</th>
                <th className="p-2">Status</th>
                <th className="p-2">Order Date</th>
                <th className="p-2">Total</th>
                <th className="p-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const supplier = suppliers.find((s) => s.id === o.supplier_id);
                const isReceivable = ["draft", "submitted", "acknowledged"].includes(o.status);
                return (
                  <tr key={o.id} className="border-b border-slate-100">
                    <td className="p-2 font-medium">{o.po_number}</td>
                    <td className="p-2">{supplier?.name ?? `Supplier #${o.supplier_id}`}</td>
                    <td className="p-2">
                      <span className="badge bg-slate-100 text-slate-700">{o.status}</span>
                    </td>
                    <td className="p-2">{o.order_date}</td>
                    <td className="p-2">Rs {o.total_amount}</td>
                    <td className="p-2">
                      {isReceivable ? (
                        <button className="btn-primary" onClick={() => void receiveOrder(o.id, o.status)}>
                          Receive
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500">Completed</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
