import React from 'react';
import { ArrowUpRight, PlusCircle, CreditCard, Lock, CheckCircle2, XCircle } from 'lucide-react';

export const AccountCard = ({ account, onSend, onDeposit, isSelected, onSelect }) => {
  const isFrozen = account.status === 'FROZEN';
  const isClosed = account.status === 'CLOSED';
  const formattedBalance = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(parseFloat(account.balance || 0));

  const getStatusBadge = () => {
    switch (account.status) {
      case 'ACTIVE':
        return <span className="badge badge-active"><CheckCircle2 size={12} /> Active</span>;
      case 'FROZEN':
        return <span className="badge badge-frozen"><Lock size={12} /> Frozen</span>;
      case 'CLOSED':
        return <span className="badge badge-closed"><XCircle size={12} /> Closed</span>;
      default:
        return <span className="badge">{account.status}</span>;
    }
  };

  return (
    <div
      className="card"
      onClick={() => onSelect && onSelect(account)}
      style={{
        cursor: onSelect ? 'pointer' : 'default',
        position: 'relative',
        overflow: 'hidden',
        border: isSelected ? '1px solid #3b82f6' : '1px solid var(--border-color)',
        boxShadow: isSelected ? '0 0 20px rgba(59, 130, 246, 0.25)' : 'var(--shadow-main)',
        background: isSelected
          ? 'linear-gradient(145deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95))'
          : 'var(--bg-card)'
      }}
    >
      <div style={{
        position: 'absolute',
        right: '-20px',
        bottom: '-20px',
        opacity: 0.04,
        pointerEvents: 'none'
      }}>
        <CreditCard size={160} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
        <div>
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Account #{account.account_id}
          </span>
          <div className="mono" style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
            {account.account_number}
          </div>
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
          Available Balance
        </div>
        <div className="mono" style={{ fontSize: '1.875rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.02em' }}>
          {formattedBalance}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
        <button
          className="btn btn-primary"
          onClick={(e) => {
            e.stopPropagation();
            onSend(account);
          }}
          disabled={isFrozen || isClosed}
          style={{ flex: 1, padding: '0.5rem 0.75rem', fontSize: '0.8125rem' }}
        >
          <ArrowUpRight size={16} />
          Transfer
        </button>

        <button
          className="btn btn-emerald"
          onClick={(e) => {
            e.stopPropagation();
            onDeposit(account);
          }}
          disabled={isClosed}
          style={{ padding: '0.5rem 0.875rem', fontSize: '0.8125rem' }}
          title="Deposit Simulation Funds"
        >
          <PlusCircle size={16} />
          Deposit
        </button>
      </div>
    </div>
  );
};
