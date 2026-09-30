import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api, apiError } from "../services/api";
import type { ProductDetail } from "../types";

export function ProductDetailsPage() {
  const { id } = useParams();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stockForm, setStockForm] = useState({
    movement_type: "adjustment",
    quantity: 0,
    reference_number: "",
    notes: "",
  });

  const load = async () => {
    if (!id) {
      return;
    }
    try {
      const res = await api.get<ProductDetail>(`/products/${id}`);
      setProduct(res.data);
    } catch (err) {
      setError(apiError(err));
    }
  };

  useEffect(() => {
    void load();
  }, [id]);

  const onStockUpdate = async (e: FormEvent) => {
    e.preventDefault();
    if (!id) {
      return;
    }
    try {
      await api.patch(`/products/${id}/stock`, {
        ...stockForm,
        quantity: Number(stockForm.quantity),
      });
      await load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  if (error) {
    return <div className="card text-sm text-red-700">{error}</div>;
  }

  if (!product) {
    return <div className="card text-sm text-slate-600">Loading product details...</div>;
  }

  return (
    <div className="space-y-4">
      <section className="card">
        <h1 className="font-heading text-2xl font-bold">{product.name}</h1>
        <p className="mt-1 text-sm text-slate-600">SKU: {product.sku}</p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat title="Category" value={product.category} />
          <Stat title="Available" value={product.stock_level?.quantity_available ?? 0} />
          <Stat title="On Hand" value={product.stock_level?.quantity_on_hand ?? 0} />
          <Stat title="Reorder Point" value={product.reorder_point} />
        </div>
      </section>

      <section className="card">
        <h2 className="mb-3 font-heading text-lg font-semibold">Update Stock</h2>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={onStockUpdate}>
          <select
            className="input"
            value={stockForm.movement_type}
            onChange={(e) => setStockForm((prev) => ({ ...prev, movement_type: e.target.value }))}
          >
            <option value="receipt">receipt</option>
            <option value="sale">sale</option>
            <option value="adjustment">adjustment</option>
            <option value="transfer">transfer</option>
            <option value="return">return</option>
          </select>
          <input
            className="input"
            type="number"
            placeholder="Quantity (negative for outgoing)"
            value={stockForm.quantity}
            onChange={(e) => setStockForm((prev) => ({ ...prev, quantity: Number(e.target.value) }))}
          />
          <input
            className="input"
            placeholder="Reference number"
            value={stockForm.reference_number}
            onChange={(e) => setStockForm((prev) => ({ ...prev, reference_number: e.target.value }))}
          />
          <input
            className="input"
            placeholder="Notes"
            value={stockForm.notes}
            onChange={(e) => setStockForm((prev) => ({ ...prev, notes: e.target.value }))}
          />
          <div className="md:col-span-2">
            <button className="btn-primary" type="submit">
              Record Movement
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2 className="mb-3 font-heading text-lg font-semibold">Recent Movements</h2>
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left">
                <th className="p-2">Type</th>
                <th className="p-2">Quantity</th>
                <th className="p-2">Reference</th>
                <th className="p-2">By</th>
                <th className="p-2">At</th>
              </tr>
            </thead>
            <tbody>
              {product.movements.map((m) => (
                <tr key={m.id} className="border-b border-slate-100">
                  <td className="p-2">{m.movement_type}</td>
                  <td className="p-2">{m.quantity}</td>
                  <td className="p-2">{m.reference_number ?? "-"}</td>
                  <td className="p-2">{m.recorded_by}</td>
                  <td className="p-2">{new Date(m.recorded_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Stat({ title, value }: Readonly<{ title: string; value: string | number }>) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 font-heading text-xl font-semibold">{value}</p>
    </div>
  );
}
