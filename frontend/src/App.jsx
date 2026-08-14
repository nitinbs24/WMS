import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/useAuthStore';

// Pages (stubs — full implementation in Phase 2–6)
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import DigitalTwinPage from './pages/DigitalTwinPage';
import RunConfigPage from './pages/RunConfigPage';
import RunHistoryPage from './pages/RunHistoryPage';
import AdminSettingsPage from './pages/AdminSettingsPage';
import AppShell from './components/layout/AppShell';

/** Route guard — redirect to login if no token */
function ProtectedRoute({ children }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Protected app routes share the AppShell layout */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="twin" element={<DigitalTwinPage />} />
          <Route path="runs" element={<RunHistoryPage />} />
          <Route path="runs/new" element={<RunConfigPage />} />
          <Route path="admin/settings" element={<AdminSettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
