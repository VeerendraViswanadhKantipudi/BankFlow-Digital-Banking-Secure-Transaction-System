import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { BrandingProvider } from './context/BrandingContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ShieldCheck } from 'lucide-react';

const AppInner = () => {
  const { isAuthenticated, loading } = useAuth();
  const [authView, setAuthView] = useState('login');

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)'
      }}>
        <div style={{
          background: 'linear-gradient(135deg, var(--brand-primary), var(--brand-accent))',
          padding: '1rem',
          borderRadius: '20px',
          boxShadow: '0 0 30px rgba(59, 130, 246, 0.4)',
          marginBottom: '1.25rem'
        }}>
          <ShieldCheck size={36} color="#ffffff" />
        </div>
        <div style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
          Securing Ledger Connection...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return authView === 'login' ? (
      <LoginPage onSwitchToRegister={() => setAuthView('register')} />
    ) : (
      <RegisterPage onSwitchToLogin={() => setAuthView('login')} />
    );
  }

  return <DashboardPage />;
};

export const App = () => (
  <BrandingProvider>
    <AppInner />
  </BrandingProvider>
);

export default App;
