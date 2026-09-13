import React, { useState } from 'react';
import { accountApi } from '../api/client';
import { CreditCard, X, AlertCircle, CheckCircle2 } from 'lucide-react';

export const CreateAccountModal = ({ isOpen, onClose, onSuccess }) => {
  const [initialDeposit, setInitialDeposit] = useState('0.00');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const deposit = parseFloat(initialDeposit || 0);
    if (deposit < 0) {
      setError('Initial deposit cannot be negative.');
      return;
    }

    setLoading(true);
    try {
      await accountApi.create({
        initial_deposit: deposit.toFixed(2)
      });
      setSuccess('Secondary bank account provisioned successfully!');
      setTimeout(() => {
        onSuccess && onSuccess();
        onClose();
      }, 1200);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Account creation failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <div style={{
              background: 'rgba(59, 130, 246, 0.15)',
              padding: '0.5rem',
              borderRadius: '8px',
              color: '#3b82f6'
            }}>
              <CreditCard size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ffffff' }}>Open New Account</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Instant Account Number Generation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.25rem'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="alert alert-success">
            <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">Initial Deposit (USD)</label>
            <input
              type="number"
              step="0.01"
              className="input-field mono"
              placeholder="0.00"
              value={initialDeposit}
              onChange={(e) => setInitialDeposit(e.target.value)}
              min="0.00"
              autoFocus
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Set starting balance or leave 0.00.
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              style={{ flex: 1 }}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              style={{ flex: 1.5 }}
              disabled={loading}
            >
              {loading ? 'Provisioning...' : 'Open Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
