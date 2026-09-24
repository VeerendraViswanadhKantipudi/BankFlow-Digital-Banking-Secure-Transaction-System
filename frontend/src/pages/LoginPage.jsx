import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, ArrowRight, AlertCircle, User, Shield, Sparkles } from 'lucide-react';

export const LoginPage = ({ onSwitchToRegister }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Login failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError(null);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
      background: 'radial-gradient(ellipse at 50% 10%, rgba(37, 99, 235, 0.18), var(--bg-primary) 65%)'
    }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex',
            background: 'linear-gradient(135deg, #2563eb, #3b82f6)',
            padding: '1rem',
            borderRadius: '20px',
            boxShadow: '0 0 30px rgba(59, 130, 246, 0.45)',
            marginBottom: '1rem'
          }}>
            <ShieldCheck size={36} color="#ffffff" />
          </div>
          <h1 style={{ fontSize: '2rem', fontWeight: '800', letterSpacing: '-0.03em', color: '#ffffff' }}>
            Bank<span style={{ color: '#3b82f6' }}>Flow</span>
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
            Double-Entry Digital Banking & Secure Transaction System
          </p>
        </div>

        <div className="card">
          <h2 style={{ fontSize: '1.35rem', fontWeight: '800', marginBottom: '0.35rem', color: '#ffffff' }}>Welcome Back</h2>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
            Enter your credentials or click a demo profile below.
          </p>

          {/* Quick Demo Login Pill for Customers */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              ⚡ 1-Click Demo Accounts (Customer)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleQuickLogin('alice@example.com', 'Password123!')}
                style={{ fontSize: '0.75rem', padding: '0.45rem 0.5rem', width: '100%', justifyContent: 'center' }}
              >
                <User size={14} color="#3b82f6" />
                <span>Alice ($2,500)</span>
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => handleQuickLogin('bob@example.com', 'Password123!')}
                style={{ fontSize: '0.75rem', padding: '0.45rem 0.5rem', width: '100%', justifyContent: 'center' }}
              >
                <User size={14} color="#10b981" />
                <span>Bob ($1,500)</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="alert alert-error" style={{ marginBottom: '1.25rem' }}>
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="input-group">
              <label className="input-label">Email Address</label>
              <input
                type="email"
                className="input-field"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="input-group">
              <label className="input-label">Password</label>
              <input
                type="password"
                className="input-field"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '0.5rem', padding: '0.75rem' }}
              disabled={loading}
            >
              {loading ? 'Authenticating (Timing-Safe)...' : (
                <>
                  Sign In <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Don't have an account yet?{' '}
            <button
              onClick={onSwitchToRegister}
              style={{ background: 'none', border: 'none', color: '#3b82f6', fontWeight: '600', cursor: 'pointer', padding: 0 }}
            >
              Register now
            </button>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          🔒 MySQL (InnoDB) Row-Level Locks • Rate Limited • Audit Logged
        </div>
      </div>
    </div>
  );
};
