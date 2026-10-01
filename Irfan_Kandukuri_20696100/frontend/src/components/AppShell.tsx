import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../state/AuthContext";
import type { Role } from "../types";

type NavItem = {
  to: string;
  label: string;
  icon: string;
  roles: Role[];
};

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: "⌂", roles: ["admin", "manager"] },
  { to: "/assistant", label: "Assistant", icon: "✦", roles: ["admin", "manager", "analyst", "procurement", "staff"] },
  { to: "/products", label: "Products", icon: "▦", roles: ["admin", "manager", "analyst", "procurement", "staff"] },
  { to: "/suppliers", label: "Suppliers", icon: "◎", roles: ["admin", "manager", "procurement"] },
  { to: "/orders", label: "Purchase Orders", icon: "↗", roles: ["admin", "manager", "procurement", "staff"] },
  { to: "/alerts", label: "Stock Alerts", icon: "△", roles: ["admin", "manager"] },
];

type AppShellProps = Readonly<{ children: React.ReactNode }>;

export function AppShell({ children }: AppShellProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const allowed = navItems.filter((item) => (user ? item.roles.includes(user.role) : false));

  const onLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-shell bg-slate-50 min-h-screen text-slate-800">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur-md">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button className="btn-muted px-2.5 py-1.5 md:hidden" aria-label="Open navigation" onClick={() => setMobileOpen((open) => !open)}>☰</button>
            <Link to="/dashboard" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 font-heading text-lg font-bold text-white shadow-sm shadow-teal-600/20">P</span>
              <span className="hidden sm:block"><span className="block font-heading text-sm font-bold tracking-tight text-slate-900">POC-07</span><span className="block text-[10px] uppercase font-semibold tracking-wider text-teal-600">Inventory OS</span></span>
            </Link>
          </div>
          <div className="hidden max-w-md flex-1 px-8 md:block">
            <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-1.5 text-sm text-slate-400 focus-within:border-teal-600 focus-within:bg-white transition-all">
              <span>⌕</span>
              <span className="text-slate-400 text-xs">Search catalog, suppliers, purchase orders...</span>
              <kbd className="ml-auto rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-400 font-mono">⌘ K</kbd>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-xs font-semibold text-slate-900 leading-tight">{user?.full_name}</p>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-teal-700">{user?.role}</p>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-100 text-xs font-bold text-teal-800 border border-teal-200">
              {user?.full_name?.charAt(0) ?? "U"}
            </div>
            <button className="btn-muted px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900" onClick={onLogout}>Logout</button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1600px] gap-0">
        <aside className={`shell-sidebar fixed inset-y-[64px] left-0 z-20 w-[240px] bg-slate-900 border-r border-slate-800 p-4 transition-transform duration-300 md:sticky md:top-[64px] md:block md:h-[calc(100vh-64px)] md:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="mb-5 rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-teal-400">Workspace</p>
            <p className="mt-1 font-heading text-xs font-bold text-slate-200">Inventory Management</p>
            <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
              <span className="h-2 w-2 rounded-full bg-teal-400" /> API Connected
            </div>
          </div>
          <p className="mb-2 px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">Main Menu</p>
          <nav className="flex flex-col gap-1">
            {allowed.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `nav-link ${isActive ? "nav-link-active" : ""}`
                }
              >
                <span className="w-5 text-center text-base">{item.icon}</span><span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </aside>

        {mobileOpen ? <button className="fixed inset-0 z-10 bg-slate-900/40 backdrop-blur-sm md:hidden" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /> : null}
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
