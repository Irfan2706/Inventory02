import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardPage } from "./pages/DashboardPage";
import { InventoryAssistantPage } from "./pages/InventoryAssistantPage";
import { LoginPage } from "./pages/LoginPage";
import { LowStockAlertsPage } from "./pages/LowStockAlertsPage";
import { ProductDetailsPage } from "./pages/ProductDetailsPage";
import { ProductsPage } from "./pages/ProductsPage";
import { PurchaseOrdersPage } from "./pages/PurchaseOrdersPage";
import { SuppliersPage } from "./pages/SuppliersPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager"]}>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/assistant"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager", "analyst", "procurement", "staff"]}>
            <AppShell>
              <InventoryAssistantPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/products"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager", "analyst", "procurement", "staff"]}>
            <AppShell>
              <ProductsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/products/:id"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager", "analyst", "procurement", "staff"]}>
            <AppShell>
              <ProductDetailsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/suppliers"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager", "procurement"]}>
            <AppShell>
              <SuppliersPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/orders"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager", "procurement", "staff"]}>
            <AppShell>
              <PurchaseOrdersPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/alerts"
        element={
          <ProtectedRoute allowedRoles={["admin", "manager"]}>
            <AppShell>
              <LowStockAlertsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<Navigate to="/products" replace />} />
      <Route path="*" element={<Navigate to="/products" replace />} />
    </Routes>
  );
}
