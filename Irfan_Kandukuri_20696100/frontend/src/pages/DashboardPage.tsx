import { useEffect, useState } from "react";

import { api, apiError } from "../services/api";
import type { DashboardSummary } from "../types";

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await api.get<DashboardSummary>("/dashboard");
        setData(res.data);
      } catch (err) {
        setError(apiError(err));
      }
    };
    void run();
  }, []);

  if (error) {
    return <div className="card text-sm text-red-700">{error}</div>;
  }

  if (!data) {
    return <div className="space-y-6"><div className="h-10 w-72 rounded-xl skeleton" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[1, 2, 3, 4].map((item) => <div className="card h-36 skeleton" key={item} />)}</div></div>;
  }

  const metrics = [
    { label: "Total Products", value: data.total_products, icon: "▦", tone: "from-indigo-500 to-blue-500", note: "Active catalog" },
    { label: "Low Stock Alerts", value: data.low_stock_count, icon: "△", tone: "from-amber-500 to-orange-400", note: "Needs attention" },
    { label: "Open Purchase Orders", value: data.open_po_count, icon: "↗", tone: "from-cyan-500 to-teal-400", note: "In workflow" },
    { label: "Inventory Value", value: `Rs ${data.total_stock_value.toLocaleString()}`, icon: "◈", tone: "from-fuchsia-500 to-indigo-500", note: "Current valuation" },
  ];

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-xs font-bold uppercase tracking-[.22em] text-cyan-300">Tuesday, August 18</p><h1 className="mt-2 font-heading text-3xl font-extrabold tracking-tight text-white sm:text-4xl">Good morning, {"Manager"}</h1><p className="mt-2 text-sm text-slate-400">Here is the operational pulse across your inventory network.</p></div><button className="btn-primary self-start sm:self-auto">+ New purchase order</button></section>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((item) => (
          <article key={item.label} className="card group relative overflow-hidden transition duration-300 hover:-translate-y-1 hover:border-white/20">
            <div className={`absolute -right-8 -top-8 h-28 w-28 rounded-full bg-gradient-to-br ${item.tone} opacity-20 blur-2xl transition group-hover:opacity-40`} />
            <div className="relative flex items-start justify-between"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.label}</p><p className="mt-3 font-heading text-3xl font-extrabold text-white">{item.value}</p><p className="mt-2 text-xs text-slate-500">{item.note}</p></div><span className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${item.tone} text-lg font-bold text-white shadow-lg`}>{item.icon}</span></div>
          </article>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.35fr_.65fr]">
        <section className="card min-h-[300px]"><div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-slate-500">Inventory activity</p><h2 className="mt-2 font-heading text-xl font-bold text-white">Stock movement overview</h2></div><span className="badge bg-cyan-400/10 text-cyan-300">Last 30 days</span></div><div className="mt-8 flex h-40 items-end gap-2 sm:gap-4">{[{id:"w1",height:42},{id:"w2",height:58},{id:"w3",height:45},{id:"w4",height:74},{id:"w5",height:62},{id:"w6",height:88},{id:"w7",height:70},{id:"w8",height:96},{id:"w9",height:78},{id:"w10",height:82},{id:"w11",height:68},{id:"w12",height:90}].map((bar, index) => <div className="group flex flex-1 flex-col items-center gap-2" key={bar.id}><div className="w-full rounded-t-lg bg-gradient-to-t from-indigo-600/70 to-cyan-400/80 transition group-hover:from-indigo-400 group-hover:to-cyan-300" style={{ height: `${bar.height}%` }} /><span className="text-[10px] text-slate-600">{index + 1}</span></div>)}</div></section>
        <section className="card"><div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-slate-500">Health score</p><h2 className="mt-2 font-heading text-xl font-bold text-white">Inventory health</h2></div><span className="text-2xl font-extrabold text-emerald-400">{Math.max(0, 100 - data.low_stock_count)}%</span></div><div className="mt-8 flex items-center justify-center"><div className="relative flex h-40 w-40 items-center justify-center rounded-full" style={{ background: `conic-gradient(#34d399 0 ${Math.max(0, 100 - data.low_stock_count)}%, rgba(255,255,255,.08) 0)` }}><div className="flex h-32 w-32 flex-col items-center justify-center rounded-full bg-slate-900"><span className="font-heading text-3xl font-extrabold text-white">{data.out_of_stock_count}</span><span className="text-xs text-slate-500">out of stock</span></div></div></div><div className="mt-6 flex justify-between border-t border-white/10 pt-4 text-xs text-slate-500"><span>Healthy items</span><span className="text-slate-300">{data.total_products - data.low_stock_count}</span></div></section>
      </div>
      <section className="card"><div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[.18em] text-slate-500">Attention queue</p><h2 className="mt-2 font-heading text-xl font-bold text-white">Next best actions</h2></div><span className="text-xs text-cyan-300">View all →</span></div><div className="mt-5 grid gap-3 md:grid-cols-3"><div className="rounded-xl border border-amber-400/15 bg-amber-400/[.06] p-4"><span className="text-xl text-amber-300">△</span><p className="mt-3 text-sm font-semibold text-white">Review low stock</p><p className="mt-1 text-xs text-slate-500">{data.low_stock_count} items need procurement review.</p></div><div className="rounded-xl border border-cyan-400/15 bg-cyan-400/[.06] p-4"><span className="text-xl text-cyan-300">↗</span><p className="mt-3 text-sm font-semibold text-white">Track open orders</p><p className="mt-1 text-xs text-slate-500">{data.open_po_count} purchase orders in progress.</p></div><div className="rounded-xl border border-indigo-400/15 bg-indigo-400/[.06] p-4"><span className="text-xl text-indigo-300">✦</span><p className="mt-3 text-sm font-semibold text-white">Ask the assistant</p><p className="mt-1 text-xs text-slate-500">Get policy and inventory guidance instantly.</p></div></div></section>
    </div>
  );
}
