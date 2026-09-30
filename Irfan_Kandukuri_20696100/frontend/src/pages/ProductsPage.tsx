import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, apiError } from "../services/api";
import type { Product, Supplier } from "../types";

const categories = ["grocery", "electronics", "clothing", "household", "personal_care"];

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");

  const [form, setForm] = useState({
    name: "",
    category: "grocery",
    unit_price: 0,
    cost_price: 0,
    unit_of_measure: "pieces",
    reorder_point: 10,
    reorder_quantity: 50,
    supplier_id: "",
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pRes, sRes] = await Promise.all([api.get<Product[]>("/products"), api.get<Supplier[]>("/suppliers")]);
      setProducts(pRes.data);
      setSuppliers(sRes.data);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const filtered = useMemo(() => {
    if (!categoryFilter) {
      return products;
    }
    return products.filter((item) => item.category === categoryFilter);
  }, [products, categoryFilter]);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/products", {
        ...form,
        supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
      });
      setForm({
        name: "",
        category: "grocery",
        unit_price: 0,
        cost_price: 0,
        unit_of_measure: "pieces",
        reorder_point: 10,
        reorder_quantity: 50,
        supplier_id: "",
      });
      await loadData();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const onEdit = async (product: Product) => {
    const name = window.prompt("Product name", product.name);
    if (!name) {
      return;
    }

    const reorderPointRaw = window.prompt("Reorder point", String(product.reorder_point));
    if (reorderPointRaw === null) {
      return;
    }

    const reorderQuantityRaw = window.prompt("Reorder quantity", String(product.reorder_quantity));
    if (reorderQuantityRaw === null) {
      return;
    }

    try {
      await api.put(`/products/${product.id}`, {
        name,
        reorder_point: Number(reorderPointRaw),
        reorder_quantity: Number(reorderQuantityRaw),
      });
      await loadData();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const onDelete = async (product: Product) => {
    const approved = window.confirm(`Delete product ${product.sku} - ${product.name}?`);
    if (!approved) {
      return;
    }

    try {
      await api.delete(`/products/${product.id}`);
      await loadData();
    } catch (err) {
      setError(apiError(err));
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="font-heading text-2xl font-bold">Products</h1>

      <section className="card">
        <h2 className="mb-3 font-heading text-lg font-semibold">Create Product</h2>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
          <input
            className="input"
            placeholder="Product name"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <select
            className="input"
            value={form.category}
            onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>

          <input
            className="input"
            type="number"
            min={0}
            step="0.01"
            placeholder="Unit price"
            value={form.unit_price}
            onChange={(e) => setForm((prev) => ({ ...prev, unit_price: Number(e.target.value) }))}
            required
          />
          <input
            className="input"
            type="number"
            min={0}
            step="0.01"
            placeholder="Cost price"
            value={form.cost_price}
            onChange={(e) => setForm((prev) => ({ ...prev, cost_price: Number(e.target.value) }))}
            required
          />

          <input
            className="input"
            placeholder="Unit of measure"
            value={form.unit_of_measure}
            onChange={(e) => setForm((prev) => ({ ...prev, unit_of_measure: e.target.value }))}
          />
          <select
            className="input"
            value={form.supplier_id}
            onChange={(e) => setForm((prev) => ({ ...prev, supplier_id: e.target.value }))}
          >
            <option value="">No supplier</option>
            {suppliers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>

          <input
            className="input"
            type="number"
            min={0}
            placeholder="Reorder point"
            value={form.reorder_point}
            onChange={(e) => setForm((prev) => ({ ...prev, reorder_point: Number(e.target.value) }))}
            required
          />
          <input
            className="input"
            type="number"
            min={1}
            placeholder="Reorder quantity"
            value={form.reorder_quantity}
            onChange={(e) => setForm((prev) => ({ ...prev, reorder_quantity: Number(e.target.value) }))}
            required
          />

          <div className="md:col-span-2">
            <button className="btn-primary" type="submit">
              Create Product
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-heading text-lg font-semibold">Product List</h2>
          <select className="input max-w-xs" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        {loading ? <p className="text-sm text-slate-600">Loading...</p> : null}
        {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}

        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left">
                <th className="p-2">SKU</th>
                <th className="p-2">Name</th>
                <th className="p-2">Category</th>
                <th className="p-2">Price</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} className="border-b border-slate-100">
                  <td className="p-2 font-medium">{item.sku}</td>
                  <td className="p-2">{item.name}</td>
                  <td className="p-2">{item.category}</td>
                  <td className="p-2">Rs {item.unit_price}</td>
                  <td className="p-2">
                    <div className="flex flex-wrap gap-2">
                      <Link className="btn-muted" to={`/products/${item.id}`}>
                        Details
                      </Link>
                      <button className="btn-muted" onClick={() => void onEdit(item)} type="button">
                        Edit
                      </button>
                      <button className="btn-muted" onClick={() => void onDelete(item)} type="button">
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
