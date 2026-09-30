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
    <div className="app-shell">
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#080d19]/80 backdrop-blur-xl">
        <div className="flex h-[72px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button className="btn-muted px-3 md:hidden" aria-label="Open navigation" onClick={() => setMobileOpen((open) => !open)}>☰</button>
            <Link to="/dashboard" className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 font-heading text-lg font-bold text-white shadow-lg shadow-cyan-950/40">P</span>
              <span className="hidden sm:block"><span className="block font-heading text-sm font-extrabold tracking-tight text-white">POC-07</span><span className="block text-[10px] uppercase tracking-[.2em] text-slate-500">Inventory OS</span></span>
            </Link>
          </div>
          <div className="hidden max-w-md flex-1 px-8 md:block">
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[.04] px-3 py-2 text-sm text-slate-500"><span>⌕</span><span>Search inventory, orders, suppliers...</span><kbd className="ml-auto rounded border border-white/10 px-1.5 py-0.5 text-[10px] text-slate-600">⌘ K</kbd></div>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <button className="hidden rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-white sm:block" aria-label="Notifications">♢</button>
            <div className="hidden text-right sm:block"><p className="text-sm font-semibold text-white">{user?.full_name}</p><p className="text-[10px] uppercase tracking-[.16em] text-cyan-300">{user?.role}</p></div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 text-sm font-bold text-white">{user?.full_name?.charAt(0) ?? "U"}</div>
            <button className="btn-muted hidden px-3 py-2 text-xs sm:inline-flex" onClick={onLogout}>Logout</button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1600px] gap-0">
        <aside className={`shell-sidebar fixed inset-y-[72px] left-0 z-20 w-[252px] border-r p-4 transition-transform duration-300 md:sticky md:top-[72px] md:block md:h-[calc(100vh-72px)] md:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <div className="mb-6 rounded-2xl border border-indigo-400/20 bg-gradient-to-br from-indigo-500/15 to-cyan-400/5 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[.2em] text-cyan-300">Workspace</p>
            <p className="mt-2 font-heading text-sm font-bold text-white">Operations command center</p>
            <div className="mt-4 flex items-center gap-2 text-xs text-slate-400"><span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" /> Systems operational</div>
          </div>
          <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[.2em] text-slate-600">Workspace</p>
          <nav className="flex flex-col gap-1">
            {allowed.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `nav-link rounded-xl px-3 py-2.5 text-sm font-medium ${isActive ? "nav-link-active" : ""}`
                }
              >
                <span className="w-5 text-center text-base">{item.icon}</span><span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto hidden border-t border-white/10 pt-4 md:block"><p className="px-3 text-[10px] font-bold uppercase tracking-[.2em] text-slate-600">System</p><button className="nav-link mt-2 w-full rounded-xl px-3 py-2.5 text-left text-sm"><span className="w-5 text-center">⚙</span> Settings</button></div>
        </aside>

        {mobileOpen ? <button className="fixed inset-0 z-10 bg-black/50 md:hidden" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /> : null}
        <main className="page-enter min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
