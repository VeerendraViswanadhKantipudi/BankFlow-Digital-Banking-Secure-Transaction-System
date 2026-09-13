import React from 'react';
import { ArrowUpRight, ArrowDownLeft, CheckCircle2, Clock, XCircle, Filter, ChevronLeft, ChevronRight } from 'lucide-react';

export const TransactionTable = ({
  transactions,
  pagination,
  userAccounts,
  loading,
  filters,
  onFilterChange,
  onPageChange
}) => {
  const userAccountIds = new Set(userAccounts.map(a => a.account_id));

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="badge badge-completed"><CheckCircle2 size={12} /> Completed</span>;
      case 'PENDING':
        return <span className="badge badge-pending"><Clock size={12} /> Pending</span>;
      case 'FAILED':
        return <span className="badge badge-failed"><XCircle size={12} /> Failed</span>;
      default:
        return <span className="badge">{status}</span>;
    }
  };

  const getDirectionInfo = (tx) => {
    const isSender = userAccountIds.has(tx.sender_account_id);
    const isReceiver = userAccountIds.has(tx.receiver_account_id);

    if (isSender && isReceiver) {
      return {
        label: 'Internal Transfer',
        color: '#3b82f6',
        icon: <ArrowUpRight size={14} color="#3b82f6" />,
        prefix: '±'
      };
    } else if (isSender) {
      return {
        label: 'Sent to Account #' + tx.receiver_account_id,
        color: '#f43f5e',
        icon: <ArrowUpRight size={14} color="#f43f5e" />,
        prefix: '-'
      };
    } else {
      return {
        label: 'Received from Account #' + tx.sender_account_id,
        color: '#10b981',
        icon: <ArrowDownLeft size={14} color="#10b981" />,
        prefix: '+'
      };
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="card" style={{ marginTop: '2rem' }}>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '1rem',
        marginBottom: '1.25rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div>
          <h3 style={{ fontSize: '1.125rem', fontWeight: '700', color: '#ffffff' }}>Transaction Ledger</h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Immutable Double-Entry Ledger History
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Filter size={14} color="var(--text-muted)" />
            <select
              className="input-field"
              style={{ padding: '0.4rem 0.6rem', fontSize: '0.8125rem', width: 'auto' }}
              value={filters.type || 'ALL'}
              onChange={(e) => onFilterChange({ ...filters, type: e.target.value, page: 1 })}
            >
              <option value="ALL">All Flow Types</option>
              <option value="SENT">Sent Transfers</option>
              <option value="RECEIVED">Received Transfers</option>
            </select>
          </div>

          <select
            className="input-field"
            style={{ padding: '0.4rem 0.6rem', fontSize: '0.8125rem', width: 'auto' }}
            value={filters.status || ''}
            onChange={(e) => onFilterChange({ ...filters, status: e.target.value, page: 1 })}
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>TX ID</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>Timestamp</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>Accounts (From → To)</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>Flow Details</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>Amount</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>Status</th>
              <th style={{ padding: '0.75rem 1rem', fontWeight: '600', fontSize: '0.75rem', textTransform: 'uppercase' }}>Idempotency Key</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Loading transaction ledger...
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No transactions found matching your criteria.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const dir = getDirectionInfo(tx);
                return (
                  <tr
                    key={tx.transaction_id}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                      transition: 'background 0.15s ease'
                    }}
                  >
                    <td className="mono" style={{ padding: '0.875rem 1rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                      #{tx.transaction_id}
                    </td>
                    <td className="mono" style={{ padding: '0.875rem 1rem', color: 'var(--text-secondary)', fontSize: '0.8125rem' }}>
                      {formatDate(tx.created_at)}
                    </td>
                    <td style={{ padding: '0.875rem 1rem' }}>
                      <span className="mono" style={{ color: '#93c5fd', fontWeight: '600' }}>#{tx.sender_account_id}</span>
                      <span style={{ color: 'var(--text-muted)', margin: '0 0.4rem' }}>➔</span>
                      <span className="mono" style={{ color: '#6ee7b7', fontWeight: '600' }}>#{tx.receiver_account_id}</span>
                    </td>
                    <td style={{ padding: '0.875rem 1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: dir.color, fontWeight: '600', fontSize: '0.8125rem' }}>
                        {dir.icon}
                        {dir.label}
                      </div>
                    </td>
                    <td className="mono" style={{ padding: '0.875rem 1rem', fontWeight: '700', color: '#ffffff', fontSize: '0.9375rem' }}>
                      {dir.prefix}
                    </td>
                    <td style={{ padding: '0.875rem 1rem' }}>
                      {getStatusBadge(tx.status)}
                    </td>
                    <td className="mono" style={{ padding: '0.875rem 1rem', color: 'var(--text-muted)', fontSize: '0.75rem', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={tx.idempotency_key || 'None'}>
                      {tx.idempotency_key || '—'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {pagination && pagination.total_pages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '1.25rem',
          paddingTop: '1rem',
          borderTop: '1px solid var(--border-color)',
          fontSize: '0.8125rem',
          color: 'var(--text-secondary)'
        }}>
          <div>
            Showing Page <strong>{pagination.page}</strong> of <strong>{pagination.total_pages}</strong> ({pagination.total_items} transactions)
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.65rem' }}
              disabled={pagination.page <= 1}
              onClick={() => onPageChange(pagination.page - 1)}
            >
              <ChevronLeft size={16} /> Prev
            </button>
            <button
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.65rem' }}
              disabled={pagination.page >= pagination.total_pages}
              onClick={() => onPageChange(pagination.page + 1)}
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
