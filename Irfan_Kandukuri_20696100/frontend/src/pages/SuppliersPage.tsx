import { FormEvent, useEffect, useState } from "react";

import { api, apiError } from "../services/api";
import type { Supplier } from "../types";

type SupplierCatalogItem = {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  unit_cost: number;
};

export function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [catalog, setCatalog] = useState<SupplierCatalogItem[]>([]);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    supplier_code: "",
    contact_email: "",
    payment_terms_days: 30,
    lead_time_days: 7,
    is_active: true,
  });

  const load = async () => {
    try {
      const res = await api.get<Supplier[]>("/suppliers");
      setSuppliers(res.data);
    } catch (err) {
      setError(apiError(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/suppliers", form);
      setForm({
        name: "",
        supplier_code: "",
        contact_email: "",
        payment_terms_days: 30,
        lead_time_days: 7,
        is_active: true,
      });
      await load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const loadCatalog = async () => {
    if (!selectedSupplierId) {
      setCatalog([]);
      return;
    }

    try {
      const res = await api.get<SupplierCatalogItem[]>(`/suppliers/${selectedSupplierId}/catalog`);
      setCatalog(res.data);
    } catch (err) {
      setError(apiError(err));
    }
  };

  const onEditSupplier = async (supplier: Supplier) => {
    const name = window.prompt("Supplier name", supplier.name);
    if (!name) {
      return;
    }

    const contactEmail = window.prompt("Contact email", supplier.contact_email ?? "") ?? "";
    const leadTimeRaw = window.prompt("Lead time days", String(supplier.lead_time_days));
    if (leadTimeRaw === null) {
      return;
    }

    try {
      await api.put(`/suppliers/${supplier.id}`, {
        name,
        contact_email: contactEmail || null,
        lead_time_days: Number(leadTimeRaw),
      });
      await load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  const onDeleteSupplier = async (supplier: Supplier) => {
    const approved = window.confirm(`Delete supplier ${supplier.supplier_code} - ${supplier.name}?`);
    if (!approved) {
      return;
    }

    try {
      await api.delete(`/suppliers/${supplier.id}`);
      if (selectedSupplierId === String(supplier.id)) {
        setSelectedSupplierId("");
        setCatalog([]);
      }
      await load();
    } catch (err) {
      setError(apiError(err));
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="font-heading text-2xl font-bold">Suppliers</h1>

      <section className="card">
        <h2 className="mb-3 font-heading text-lg font-semibold">Create Supplier</h2>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
          <input
            className="input"
            placeholder="Supplier name"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <input
            className="input"
            placeholder="Supplier code"
            value={form.supplier_code}
            onChange={(e) => setForm((prev) => ({ ...prev, supplier_code: e.target.value }))}
            required
          />
          <input
            className="input"
            placeholder="Contact email"
            type="email"
            value={form.contact_email}
            onChange={(e) => setForm((prev) => ({ ...prev, contact_email: e.target.value }))}
          />
          <input
            className="input"
            type="number"
            value={form.payment_terms_days}
            onChange={(e) => setForm((prev) => ({ ...prev, payment_terms_days: Number(e.target.value) }))}
          />
          <input
            className="input"
            type="number"
            value={form.lead_time_days}
            onChange={(e) => setForm((prev) => ({ ...prev, lead_time_days: Number(e.target.value) }))}
          />
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
            />
            <span>Active</span>
          </label>
          <div className="md:col-span-2">
            <button className="btn-primary" type="submit">
              Save Supplier
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
                <th className="p-2">Code</th>
                <th className="p-2">Name</th>
                <th className="p-2">Email</th>
                <th className="p-2">Lead Time</th>
                <th className="p-2">Status</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.id} className="border-b border-slate-100">
                  <td className="p-2 font-medium">{s.supplier_code}</td>
                  <td className="p-2">{s.name}</td>
                  <td className="p-2">{s.contact_email ?? "-"}</td>
                  <td className="p-2">{s.lead_time_days} days</td>
                  <td className="p-2">
                    <span className={`badge ${s.is_active ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600"}`}>
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="p-2">
                    <div className="flex flex-wrap gap-2">
                      <button className="btn-muted" onClick={() => void onEditSupplier(s)} type="button">
                        Edit
                      </button>
                      <button className="btn-muted" onClick={() => void onDeleteSupplier(s)} type="button">
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

      <section className="card">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="font-heading text-lg font-semibold">Supplier Catalog</h2>
          <select
            className="input max-w-xs"
            value={selectedSupplierId}
            onChange={(e) => setSelectedSupplierId(e.target.value)}
          >
            <option value="">Select supplier</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <button className="btn-muted" onClick={() => void loadCatalog()}>
            Load Catalog
          </button>
        </div>

        {!selectedSupplierId ? <p className="text-sm text-slate-600">Choose a supplier to view product costs.</p> : null}
        {selectedSupplierId && catalog.length === 0 ? (
          <p className="text-sm text-slate-600">No catalog items for selected supplier.</p>
        ) : null}

        {catalog.length > 0 ? (
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left">
                  <th className="p-2">SKU</th>
                  <th className="p-2">Product</th>
                  <th className="p-2">Category</th>
                  <th className="p-2">Unit Cost</th>
                </tr>
              </thead>
              <tbody>
                {catalog.map((item) => (
                  <tr key={item.product_id} className="border-b border-slate-100">
                    <td className="p-2 font-medium">{item.sku}</td>
                    <td className="p-2">{item.name}</td>
                    <td className="p-2">{item.category}</td>
                    <td className="p-2">Rs {item.unit_cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
