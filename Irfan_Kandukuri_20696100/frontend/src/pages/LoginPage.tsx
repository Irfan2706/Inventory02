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
    <div className="relative flex min-h-screen items-center justify-center bg-slate-100/70 p-4 sm:p-6 lg:p-8">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-xl lg:grid-cols-12">
        {/* Left Hero Panel */}
        <div className="flex flex-col justify-between bg-gradient-to-br from-slate-900 via-slate-800 to-teal-950 p-8 text-white lg:col-span-5 sm:p-10">
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500 font-heading text-lg font-bold text-white shadow-md shadow-teal-500/20">
                P
              </span>
              <div>
                <p className="font-heading font-bold text-white leading-tight">POC-07</p>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-teal-400">Inventory OS</p>
              </div>
            </div>
            <div className="mt-16">
              <h2 className="font-heading text-3xl font-extrabold text-white leading-tight">
                Enterprise Inventory Intelligence
              </h2>
              <p className="mt-4 text-sm text-slate-300 leading-relaxed">
                Streamline procurement, monitor stock levels, and automate reorders with realtime analytics.
              </p>
            </div>
          </div>
          <div className="mt-12 flex items-center gap-2 text-xs text-slate-400 border-t border-slate-800 pt-6">
            <span className="h-2 w-2 rounded-full bg-teal-400 animate-pulse" />
            Workspace Active · POC-07 Enterprise
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="p-8 sm:p-10 lg:col-span-7 flex flex-col justify-center">
          <div>
            <span className="inline-block rounded-md bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 border border-teal-200/60">
              Account Login
            </span>
            <h1 className="mt-3 font-heading text-2xl font-bold tracking-tight text-slate-900">
              Sign in to your dashboard
            </h1>
            <p className="mt-1.5 text-sm text-slate-500">
              Enter your credential details to access your workspace.
            </p>
          </div>

          <form className="mt-8 space-y-5" onSubmit={onSubmit}>
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-700">
                Email Address
              </label>
              <input
                type="email"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-700">
                Password
              </label>
              <input
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error ? (
              <div className="rounded-xl bg-red-50 p-3.5 border border-red-200 text-sm text-red-700 font-medium">
                {error}
              </div>
            ) : null}

            <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
              {loading ? "Authenticating..." : "Sign in to Workspace"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
