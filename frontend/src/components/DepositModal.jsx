import React, { useState } from 'react';
import { accountApi } from '../api/client';
import { PlusCircle, X, AlertCircle, CheckCircle2 } from 'lucide-react';

export const DepositModal = ({ isOpen, onClose, account, onSuccess }) => {
  const [amount, setAmount] = useState('100.00');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!isOpen || !account) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const depositAmount = parseFloat(amount);
    if (isNaN(depositAmount) || depositAmount <= 0) {
      setError('Deposit amount must be greater than .00.');
      return;
    }

    setLoading(true);
    try {
      await accountApi.deposit(account.account_id, {
        amount: depositAmount.toFixed(2)
      });
      setSuccess('Successfully deposited $' + depositAmount.toFixed(2) + '!');
      setTimeout(() => {
        onSuccess && onSuccess();
        onClose();
      }, 1200);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Deposit failed.';
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
              background: 'rgba(16, 185, 129, 0.15)',
              padding: '0.5rem',
              borderRadius: '8px',
              color: '#10b981'
            }}>
              <PlusCircle size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ffffff' }}>Add Funds (Simulation)</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Account #{account.account_id} ({account.account_number})
              </p>
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
            <label className="input-label">Deposit Amount (USD)</label>
            <input
              type="number"
              step="0.01"
              className="input-field mono"
              placeholder="100.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              min="0.01"
              autoFocus
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Current balance: 
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
              className="btn btn-emerald"
              style={{ flex: 1.5 }}
              disabled={loading}
            >
              {loading ? 'Depositing...' : 'Confirm Deposit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
