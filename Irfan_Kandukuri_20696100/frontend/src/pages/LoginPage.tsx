import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { apiError } from "../services/api";
import { useAuth } from "../state/AuthContext";

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("manager@poc07.com");
  const [password, setPassword] = useState("Password@123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) {
    return <Navigate to="/products" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/products");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-600/15 blur-3xl" />
      <div className="relative grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/50 backdrop-blur-xl lg:grid-cols-[1.05fr_.95fr]">
        <div className="hidden flex-col justify-between border-r border-white/10 bg-gradient-to-br from-indigo-600/25 via-slate-950/20 to-cyan-500/10 p-10 lg:flex"><div><div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 font-heading text-xl font-extrabold text-white">P</span><div><p className="font-heading font-extrabold text-white">POC-07</p><p className="text-[10px] uppercase tracking-[.22em] text-slate-400">Inventory OS</p></div></div><h2 className="mt-20 max-w-sm font-heading text-4xl font-extrabold leading-tight tracking-tight text-white">See the whole operation clearly.</h2><p className="mt-5 max-w-sm text-sm leading-6 text-slate-400">A calm command center for products, procurement, stock health, and the decisions that keep your business moving.</p></div><div className="flex items-center gap-2 text-xs text-slate-500"><span className="h-2 w-2 rounded-full bg-emerald-400" /> Secure workspace · POC-07</div></div>
        <div className="p-7 sm:p-10">
        <div className="mb-10 flex items-center gap-3 lg:hidden"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 font-heading text-lg font-bold text-white">P</span><div><p className="font-heading font-extrabold text-white">POC-07</p><p className="text-[10px] uppercase tracking-[.2em] text-slate-500">Inventory OS</p></div></div>
        <p className="text-xs font-bold uppercase tracking-[.22em] text-cyan-300">Welcome back</p><h1 className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-white">Sign in to your workspace</h1>
        <p className="mt-2 text-sm text-slate-400">Manage products, procurement, and stock alerts from one place.</p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-300">Email</span>
            <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-300">Password</span>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>

          {error ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form></div>
      </div>
    </div>
  );
}
