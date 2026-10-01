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
  const [searchQuery, setSearchQuery] = useState("");

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
    return products.filter((item) => {
      const matchesCategory = !categoryFilter || item.category === categoryFilter;
      const matchesSearch = !searchQuery ||
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.sku.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [products, categoryFilter, searchQuery]);

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
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-teal-700">Catalog Management</p>
          <h1 className="mt-1 font-heading text-2xl font-bold tracking-tight text-slate-900">Products & Inventory Items</h1>
        </div>
      </div>

      <section className="card">
        <h2 className="font-heading text-base font-bold text-slate-900 border-b border-slate-100 pb-3 mb-4">Add New Product Catalog Entry</h2>
        <form className="grid gap-4 md:grid-cols-2 lg:grid-cols-4" onSubmit={onCreate}>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Product Name</label>
            <input
              className="input"
              placeholder="e.g. Wireless Ergonomic Mouse"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Category</label>
            <select
              className="input"
              value={form.category}
              onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
            >
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Unit Price (Selling)</label>
            <input
              className="input"
              type="number"
              min={0}
              step="0.01"
              placeholder="0.00"
              value={form.unit_price}
              onChange={(e) => setForm((prev) => ({ ...prev, unit_price: Number(e.target.value) }))}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Cost Price (Supplier)</label>
            <input
              className="input"
              type="number"
              min={0}
              step="0.01"
              placeholder="0.00"
              value={form.cost_price}
              onChange={(e) => setForm((prev) => ({ ...prev, cost_price: Number(e.target.value) }))}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Unit of Measure</label>
            <input
              className="input"
              placeholder="pieces, kg, boxes"
              value={form.unit_of_measure}
              onChange={(e) => setForm((prev) => ({ ...prev, unit_of_measure: e.target.value }))}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Primary Supplier</label>
            <select
              className="input"
              value={form.supplier_id}
              onChange={(e) => setForm((prev) => ({ ...prev, supplier_id: e.target.value }))}
            >
              <option value="">No supplier assigned</option>
              {suppliers.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Reorder Threshold Point</label>
            <input
              className="input"
              type="number"
              min={0}
              placeholder="10"
              value={form.reorder_point}
              onChange={(e) => setForm((prev) => ({ ...prev, reorder_point: Number(e.target.value) }))}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">Default Reorder Quantity</label>
            <input
              className="input"
              type="number"
              min={1}
              placeholder="50"
              value={form.reorder_quantity}
              onChange={(e) => setForm((prev) => ({ ...prev, reorder_quantity: Number(e.target.value) }))}
              required
            />
          </div>

          <div className="md:col-span-2 lg:col-span-4 flex justify-end pt-2">
            <button className="btn-primary px-6" type="submit">
              + Save Product
            </button>
          </div>
        </form>
      </section>

      <section className="card p-0 overflow-hidden">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-5 border-b border-slate-100 bg-slate-50/50">
          <div>
            <h2 className="font-heading text-base font-bold text-slate-900">Product List</h2>
            <p className="text-xs text-slate-500">Showing {filtered.length} products in inventory</p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
            <input
              type="text"
              className="input max-w-xs py-1.5 text-xs"
              placeholder="Filter by name or SKU..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <select className="input max-w-xs py-1.5 text-xs" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
              <option value="">All Categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? <p className="p-6 text-sm text-slate-500">Loading catalog data...</p> : null}
        {error ? <p className="m-5 text-sm rounded-lg bg-red-50 p-3 text-red-700">{error}</p> : null}

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Selling Price</th>
                <th>Reorder Config</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td>
                    <span className="font-mono text-xs font-bold text-teal-700 bg-teal-50 border border-teal-200/80 rounded px-2 py-0.5">
                      {item.sku}
                    </span>
                  </td>
                  <td>
                    <span className="font-semibold text-slate-900">{item.name}</span>
                  </td>
                  <td>
                    <span className="capitalize text-slate-600 text-xs bg-slate-100 rounded-md px-2 py-0.5 font-medium">
                      {item.category.replace("_", " ")}
                    </span>
                  </td>
                  <td className="font-semibold text-slate-800">
                    Rs {item.unit_price}
                  </td>
                  <td className="text-xs text-slate-500">
                    Point: {item.reorder_point} | Qty: {item.reorder_quantity}
                  </td>
                  <td className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link className="btn-muted text-xs py-1 px-2.5" to={`/products/${item.id}`}>
                        View
                      </Link>
                      <button className="btn-muted text-xs py-1 px-2.5" onClick={() => void onEdit(item)} type="button">
                        Edit
                      </button>
                      <button className="btn-muted text-xs py-1 px-2.5 hover:bg-red-50 hover:text-red-700 hover:border-red-200" onClick={() => void onDelete(item)} type="button">
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
