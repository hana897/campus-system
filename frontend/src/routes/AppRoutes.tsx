import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { LoginPage } from '../pages/auth/LoginPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { AssetListPage } from '../pages/assets/AssetListPage';
import { AssetDetailPage } from '../pages/assets/AssetDetailPage';
import { AssetFormPage } from '../pages/assets/AssetFormPage';
import { OwnerListPage } from '../pages/owners/OwnerListPage';
import { OwnerDetailPage } from '../pages/owners/OwnerDetailPage';
import { VerificationTerminalPage } from '../pages/verification/VerificationTerminalPage';
import { VerificationHistoryPage } from '../pages/verification/VerificationHistoryPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { ProfilePage } from '../pages/profile/ProfilePage';
import { SettingsPage } from '../pages/settings/SettingsPage';
import { useSecurity } from '../context/SecurityContext';

const AuthenticatedShell: React.FC = () => {
  const { isAuthenticated } = useSecurity();
  const location = useLocation();
  return isAuthenticated ? <AppShell /> : <Navigate to="/login" replace state={{ from: location }} />;
};

const SuperAdminSettings: React.FC = () => {
  const { currentUser } = useSecurity();
  return currentUser.role === 'SUPER_ADMIN' ? <SettingsPage /> : <Navigate to="/dashboard" replace />;
};

const AssetRegistrationAccess: React.FC = () => {
  const { currentUser } = useSecurity();
  return currentUser.role === 'ADMIN' || currentUser.role === 'SUPER_ADMIN'
    ? <AssetFormPage />
    : <Navigate to="/assets" replace />;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Authenticated SOC Shell */}
      <Route element={<AuthenticatedShell />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        
        {/* Assets */}
        <Route path="/assets" element={<AssetListPage />} />
        <Route path="/assets/new" element={<AssetRegistrationAccess />} />
        <Route path="/assets/:id" element={<AssetDetailPage />} />

        {/* Owners */}
        <Route path="/owners" element={<OwnerListPage />} />
        <Route path="/owners/:id" element={<OwnerDetailPage />} />

        {/* Verification */}
        <Route path="/verification" element={<VerificationTerminalPage />} />
        <Route path="/verification/history" element={<VerificationHistoryPage />} />

        {/* Reports */}
        <Route path="/reports" element={<ReportsPage />} />

        {/* Profile & Settings */}
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/users" element={<SuperAdminSettings />} />
        <Route path="/settings/:tab" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
