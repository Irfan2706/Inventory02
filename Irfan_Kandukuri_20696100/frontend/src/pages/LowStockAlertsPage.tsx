import { useEffect, useState } from "react";

import { api, apiError } from "../services/api";
import type { StockAlert } from "../types";

export function LowStockAlertsPage() {
  const [alerts, setAlerts] = useState<StockAlert[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await api.get<StockAlert[]>("/stock/low-alerts");
        setAlerts(res.data);
      } catch (err) {
        setError(apiError(err));
      }
    };
    void run();
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="font-heading text-2xl font-bold">Low Stock Alerts</h1>

      <section className="card">
        {error ? <p className="mb-3 text-sm text-red-700">{error}</p> : null}
        {alerts.length === 0 ? <p className="text-sm text-slate-600">No active low stock alerts.</p> : null}
        <div className="space-y-3">
          {alerts.map((alert) => (
            <article key={alert.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-ink">
                    {alert.product_name} <span className="text-slate-500">({alert.sku})</span>
                  </p>
                  <p className="mt-1 text-sm text-slate-700">{alert.message}</p>
                </div>
                <span
                  className={`badge ${
                    alert.alert_type === "out_of_stock" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {alert.alert_type}
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
