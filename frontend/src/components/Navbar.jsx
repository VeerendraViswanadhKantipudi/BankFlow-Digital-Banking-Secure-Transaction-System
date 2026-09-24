import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useBranding } from '../context/BrandingContext';
import { ShieldCheck, LogOut, RefreshCw, Layers, ShieldAlert, Cpu } from 'lucide-react';

export const Navbar = ({ activeTab, setActiveTab, onRefresh, refreshing }) => {
  const { user, isAdmin, logout } = useAuth();
  const { branding } = useBranding();

  return (
    <header style={{
      background: 'rgba(17, 24, 39, 0.85)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-color)',
      position: 'sticky',
      top: 0,
      zIndex: 40
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '70px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }} onClick={() => setActiveTab('overview')}>
          <div style={{
            background: `linear-gradient(135deg, var(--brand-primary), var(--brand-accent))`,
            padding: '0.5rem',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(59, 130, 246, 0.4)'
          }}>
            <ShieldCheck size={24} color="#ffffff" />
            {branding.bank_logo_url ? (
              <img src={branding.bank_logo_url} alt="Bank Logo" style={{ width: 24, height: 24, objectFit: 'contain' }} />
            ) : (
              <ShieldCheck size={24} color="#ffffff" />
            )}
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.025em', color: '#ffffff' }}>
              Bank<span style={{ color: '#3b82f6' }}>Flow</span>
              {branding.bank_name || 'BankFlow'}
            </h1>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: '600', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Transactional Banking
              {branding.bank_tagline || 'Transactional Banking'}
            </p>
          </div>
        </div>

        <nav style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className={'btn ' + (activeTab === 'overview' ? 'btn-primary' : 'btn-secondary')}
            onClick={() => setActiveTab('overview')}
            style={{ padding: '0.45rem 0.875rem', fontSize: '0.8125rem' }}
          >
            <Layers size={16} />
            Accounts & Ledger
          </button>
          
          <button
            className={'btn ' + (activeTab === 'concurrency' ? 'btn-primary' : 'btn-secondary')}
            onClick={() => setActiveTab('concurrency')}
            style={{ padding: '0.45rem 0.875rem', fontSize: '0.8125rem' }}
          >
            <Cpu size={16} />
            Concurrency Engine Lab
          </button>

          {isAdmin && (
            <button
              className={'btn ' + (activeTab === 'admin' ? 'btn-primary' : 'btn-secondary')}
              onClick={() => setActiveTab('admin')}
              style={{
                padding: '0.45rem 0.875rem',
                fontSize: '0.8125rem',
                background: activeTab === 'admin' ? 'linear-gradient(135deg, #7c3aed, #a855f7)' : undefined,
                borderColor: activeTab === 'admin' ? '#a855f7' : undefined
              }}
            >
              <ShieldAlert size={16} />
              Admin Center
            </button>
          )}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            className="btn btn-secondary"
            onClick={onRefresh}
            disabled={refreshing}
            title="Refresh data"
            style={{ padding: '0.5rem', borderRadius: '8px' }}
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          </button>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.35rem 0.75rem',
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '9999px',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: isAdmin ? '#8b5cf6' : '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: '700'
            }}>
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div style={{ lineHeight: 1.2 }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                {user?.full_name}
              </div>
              <div style={{ fontSize: '0.6875rem', color: isAdmin ? '#c084fc' : 'var(--text-secondary)', fontWeight: '600' }}>
                {isAdmin ? 'ADMINISTRATOR' : 'CUSTOMER'}
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary"
            onClick={logout}
            style={{ padding: '0.45rem 0.75rem', color: '#f43f5e', borderColor: 'rgba(244, 63, 94, 0.2)' }}
            title="Log out"
          >
            <LogOut size={16} />
            <span style={{ fontSize: '0.8125rem' }}>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};
