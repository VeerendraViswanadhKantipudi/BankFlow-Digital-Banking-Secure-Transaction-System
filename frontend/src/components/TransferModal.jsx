import React, { useState } from 'react';
import { transferApi } from '../api/client';
import { Send, X, AlertCircle, CheckCircle2, KeyRound, Sparkles } from 'lucide-react';

export const TransferModal = ({ isOpen, onClose, userAccounts, preselectedAccount, onSuccess }) => {
  const [senderId, setSenderId] = useState(preselectedAccount?.account_id || userAccounts[0]?.account_id || '');
  const [receiverId, setReceiverId] = useState('');
  const [amount, setAmount] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!isOpen) return null;

  const handleGenerateKey = () => {
    const randomKey = 'bf-tx-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
    setIdempotencyKey(randomKey);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!senderId || !receiverId || !amount) {
      setError('Please fill in all required fields.');
      return;
    }

    if (parseInt(senderId) === parseInt(receiverId)) {
      setError('Self-transfers are disallowed. Sender and Receiver account IDs must differ.');
      return;
    }

    if (parseFloat(amount) <= 0) {
      setError('Transfer amount must be strictly greater than .00.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        sender_account_id: parseInt(senderId),
        receiver_account_id: parseInt(receiverId),
        amount: parseFloat(amount).toFixed(2),
        idempotency_key: idempotencyKey.trim() || undefined
      };

      await transferApi.transfer(payload);
      setSuccess('Transfer of $' + payload.amount + ' completed successfully!');
      setTimeout(() => {
        onSuccess && onSuccess();
        onClose();
      }, 1400);
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.details || err.message || 'Transfer failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const selectedSenderAccount = userAccounts.find(a => a.account_id === parseInt(senderId));

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
              <Send size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ffffff' }}>Transfer Funds</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Atomic & Deadlock-Free Execution</p>
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
            <label className="input-label">From Account (Debit Source)</label>
            <select
              className="input-field"
              value={senderId}
              onChange={(e) => setSenderId(e.target.value)}
              required
            >
              {userAccounts.map((acc) => (
                <option key={acc.account_id} value={acc.account_id}>
                  Account #{acc.account_id} ({acc.account_number}) — Balance:  [{acc.status}]
                </option>
              ))}
            </select>
            {selectedSenderAccount && (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Available Balance: <strong className="mono" style={{ color: '#34d399' }}></strong>
              </span>
            )}
          </div>

          <div className="input-group">
            <label className="input-label">To Account ID (Credit Target)</label>
            <input
              type="number"
              className="input-field mono"
              placeholder="e.g. 2"
              value={receiverId}
              onChange={(e) => setReceiverId(e.target.value)}
              required
              min="1"
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Enter the numerical destination Account ID. Receiver ownership is validated under lock.
            </span>
          </div>

          <div className="input-group">
            <label className="input-label">Transfer Amount (USD)</label>
            <input
              type="number"
              step="0.01"
              className="input-field mono"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              min="0.01"
            />
          </div>

          <div className="input-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <KeyRound size={14} />
                Idempotency Key (Optional)
              </label>
              <button
                type="button"
                onClick={handleGenerateKey}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#3b82f6',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                <Sparkles size={12} /> Auto-Generate
              </button>
            </div>
            <input
              type="text"
              className="input-field mono"
              placeholder="Optional unique retry key (e.g. bf-tx-17250000)"
              value={idempotencyKey}
              onChange={(e) => setIdempotencyKey(e.target.value)}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Protects against network retries: replaying with same key returns existing record without re-debiting.
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
              {loading ? 'Executing Under Lock...' : 'Execute Transfer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
