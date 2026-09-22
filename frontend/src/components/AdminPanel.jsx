import React, { useState, useEffect, useCallback } from 'react';
import { accountApi } from '../api/client';
import { ConcurrencyDemo } from './ConcurrencyDemo';
import { BrandingPanel } from './BrandingPanel';
import {
  ShieldAlert,
  Lock,
  Unlock,
  XCircle,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Activity,
  FileText,
  UserCheck,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Database,
  Palette,
  Cpu
} from 'lucide-react';

export const AdminPanel = ({ userAccounts = [], onRefresh }) => {
  const [activeAdminTab, setActiveAdminTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [reconciliation, setReconciliation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reconciling, setReconciling] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [auditPage, setAuditPage] = useState(1);
  const [auditPagination, setAuditPagination] = useState({ page: 1, total_pages: 1, total_items: 0 });

  const loadAllUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await accountApi.listAllAdmin();
      setUsers(res.data.users || []);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAuditLogs = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const res = await accountApi.getAuditLogs({ page, per_page: 15 });
      setAuditLogs(res.data.audit_logs || []);
      setAuditPagination(res.data.pagination || { page: 1, total_pages: 1, total_items: 0 });
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const runReconciliation = useCallback(async () => {
    setReconciling(true);
    setError(null);
    try {
      const res = await accountApi.reconcile();
      setReconciliation(res.data.reconciliation);
      setSuccess('System financial reconciliation completed successfully.');
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Reconciliation failed.');
    } finally {
      setReconciling(false);
    }
  }, []);

  useEffect(() => {
    if (activeAdminTab === 'users') {
      loadAllUsers();
    } else if (activeAdminTab === 'audit') {
      loadAuditLogs(auditPage);
    } else if (activeAdminTab === 'reconcile') {
      runReconciliation();
    }
  }, [activeAdminTab, auditPage, loadAllUsers, loadAuditLogs, runReconciliation]);

  const handleStatusChange = async (accountId, newStatus) => {
    setUpdatingId(accountId);
    setError(null);
    setSuccess(null);
    try {
      await accountApi.updateStatus(accountId, newStatus);
      setSuccess(`Account #${accountId} status updated to ${newStatus}.`);
      await loadAllUsers();
      onRefresh && onRefresh();
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Status update failed.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleRoleChange = async (userId, currentRole) => {
    const newRole = currentRole === 'ADMIN' ? 'CUSTOMER' : 'ADMIN';
    setUpdatingId(`role-${userId}`);
    setError(null);
    setSuccess(null);
    try {
      await accountApi.updateUserRole(userId, newRole);
      setSuccess(`User #${userId} role updated to ${newRole}.`);
      await loadAllUsers();
      onRefresh && onRefresh();
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Role update failed.');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div style={{ marginTop: '1.5rem' }}>
      <div className="card">
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
          marginBottom: '1.5rem',
          paddingBottom: '1.25rem',
          borderBottom: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(99, 102, 241, 0.2))',
              padding: '0.75rem',
              borderRadius: '12px',
              color: '#a855f7',
              boxShadow: '0 0 20px rgba(168, 85, 247, 0.25)'
            }}>
              <ShieldAlert size={26} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: '800', color: '#ffffff' }}>System Administration Center</h2>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                User RBAC Governance, Immutable Security Audits & Double-Entry Reconciliation
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', background: 'rgba(15, 23, 42, 0.6)', padding: '0.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <button
              className={`btn ${activeAdminTab === 'users' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveAdminTab('users')}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
            >
              <UserCheck size={14} /> Users & Accounts
            </button>
            <button
              className={`btn ${activeAdminTab === 'audit' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveAdminTab('audit')}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
            >
              <FileText size={14} /> Audit Trail
            </button>
            <button
              className={`btn ${activeAdminTab === 'reconcile' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveAdminTab('reconcile')}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
            >
              <Database size={14} /> Reconciliation
            </button>
            <button
              className={`btn ${activeAdminTab === 'concurrency' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveAdminTab('concurrency')}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
            >
              <Cpu size={14} /> Concurrency Lab
            </button>
            <button
              className={`btn ${activeAdminTab === 'branding' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveAdminTab('branding')}
              style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
            >
              <Palette size={14} /> Branding
            </button>
          </div>
        </div>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1.25rem' }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="alert alert-success" style={{ marginBottom: '1.25rem' }}>
            <CheckCircle2 size={18} />
            <span>{success}</span>
          </div>
        )}

        {activeAdminTab === 'branding' && <BrandingPanel />}

        {/* Tab 1: Users & Accounts */}
        {activeAdminTab === 'users' && (
          <div>
            {loading ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading system users and account balances...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {users.map((u) => (
                  <div
                    key={u.user_id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.6)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-md)',
                      padding: '1.25rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{
                          width: '38px',
                          height: '38px',
                          borderRadius: '50%',
                          background: u.role === 'ADMIN' ? 'linear-gradient(135deg, #7c3aed, #a855f7)' : 'linear-gradient(135deg, #2563eb, #3b82f6)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: '800',
                          fontSize: '0.875rem'
                        }}>
                          {u.full_name?.charAt(0) || 'U'}
                        </div>
                        <div>
                          <div style={{ fontWeight: '700', color: '#ffffff', fontSize: '1rem' }}>
                            {u.full_name} <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>(User #{u.user_id})</span>
                          </div>
                          <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                            {u.email}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span className={`badge ${u.role === 'ADMIN' ? 'badge-frozen' : 'badge-active'}`}>
                          {u.role}
                        </span>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
                          disabled={updatingId === `role-${u.user_id}`}
                          onClick={() => handleRoleChange(u.user_id, u.role)}
                        >
                          {u.role === 'ADMIN' ? 'Demote to Customer' : 'Promote to Admin'}
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
                      {u.accounts?.map((acc) => (
                        <div
                          key={acc.account_id}
                          style={{
                            background: 'var(--bg-card)',
                            border: '1px solid rgba(255, 255, 255, 0.05)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '0.875rem'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                            <div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Account #{acc.account_id}</div>
                              <div className="mono" style={{ fontSize: '0.875rem', fontWeight: '600' }}>{acc.account_number}</div>
                            </div>
                            <span className={`badge badge-${acc.status.toLowerCase()}`}>
                              {acc.status}
                            </span>
                          </div>

                          <div className="mono" style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ffffff', marginBottom: '0.75rem' }}>
                            ${parseFloat(acc.balance).toFixed(2)}
                          </div>

                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            {acc.status === 'ACTIVE' ? (
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', color: '#60a5fa' }}
                                disabled={updatingId === acc.account_id}
                                onClick={() => handleStatusChange(acc.account_id, 'FROZEN')}
                              >
                                <Lock size={12} /> Freeze
                              </button>
                            ) : acc.status === 'FROZEN' ? (
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', color: '#34d399' }}
                                disabled={updatingId === acc.account_id}
                                onClick={() => handleStatusChange(acc.account_id, 'ACTIVE')}
                              >
                                <Unlock size={12} /> Unfreeze
                              </button>
                            ) : null}

                            {acc.status !== 'CLOSED' && (
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', color: '#f87171' }}
                                disabled={updatingId === acc.account_id}
                                onClick={() => handleStatusChange(acc.account_id, 'CLOSED')}
                              >
                                <XCircle size={12} /> Close
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Security Audit Trail */}
        {activeAdminTab === 'audit' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                Immutable, append-only log of authentication events, transfers, and administrative actions.
              </p>
              <button className="btn btn-secondary" onClick={() => loadAuditLogs(auditPage)} disabled={loading} style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}>
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh Logs
              </button>
            </div>

            {loading ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading audit trail...
              </div>
            ) : auditLogs.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                No audit logs recorded yet.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '0.625rem 0.75rem', textTransform: 'uppercase' }}>Log ID</th>
                      <th style={{ padding: '0.625rem 0.75rem', textTransform: 'uppercase' }}>Timestamp</th>
                      <th style={{ padding: '0.625rem 0.75rem', textTransform: 'uppercase' }}>Event Type</th>
                      <th style={{ padding: '0.625rem 0.75rem', textTransform: 'uppercase' }}>Actor ID</th>
                      <th style={{ padding: '0.625rem 0.75rem', textTransform: 'uppercase' }}>IP Address</th>
                      <th style={{ padding: '0.625rem 0.75rem', textTransform: 'uppercase' }}>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.log_id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td className="mono" style={{ padding: '0.625rem 0.75rem', color: 'var(--text-secondary)' }}>#{log.log_id}</td>
                        <td className="mono" style={{ padding: '0.625rem 0.75rem', color: 'var(--text-muted)' }}>
                          {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                        </td>
                        <td style={{ padding: '0.625rem 0.75rem' }}>
                          <span className="badge badge-active">{log.event_type}</span>
                        </td>
                        <td className="mono" style={{ padding: '0.625rem 0.75rem' }}>{log.actor_id ? `#${log.actor_id}` : 'System / Anon'}</td>
                        <td className="mono" style={{ padding: '0.625rem 0.75rem', color: 'var(--text-secondary)' }}>{log.ip_address || '127.0.0.1'}</td>
                        <td className="mono" style={{ padding: '0.625rem 0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={log.details_json}>
                          {log.details_json || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {auditPagination.total_pages > 1 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', fontSize: '0.75rem' }}>
                    <div>Page {auditPagination.page} of {auditPagination.total_pages}</div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn btn-secondary"
                        disabled={auditPage <= 1}
                        onClick={() => setAuditPage(p => p - 1)}
                        style={{ padding: '0.25rem 0.5rem' }}
                      >
                        <ChevronLeft size={14} />
                      </button>
                      <button
                        className="btn btn-secondary"
                        disabled={auditPage >= auditPagination.total_pages}
                        onClick={() => setAuditPage(p => p + 1)}
                        style={{ padding: '0.25rem 0.5rem' }}
                      >
                        <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Financial Reconciliation */}
        {activeAdminTab === 'reconcile' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '700', color: '#ffffff' }}>Live Financial Ledger Audit</h3>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  Mathematically validates sum of account balances against double-entry debits and credits.
                </p>
              </div>
              <button
                className="btn btn-emerald"
                onClick={runReconciliation}
                disabled={reconciling}
                style={{ padding: '0.5rem 1rem' }}
              >
                <RefreshCw size={16} className={reconciling ? 'animate-spin' : ''} /> Run Audit
              </button>
            </div>

            {reconciliation && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Status</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: '800', color: reconciliation.is_healthy ? '#10b981' : '#f43f5e', marginTop: '0.25rem' }}>
                    {reconciliation.status}
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total System Balances</div>
                  <div className="mono" style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff', marginTop: '0.25rem' }}>
                    ${reconciliation.total_account_balances}
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Ledger Credits</div>
                  <div className="mono" style={{ fontSize: '1.25rem', fontWeight: '800', color: '#34d399', marginTop: '0.25rem' }}>
                    ${reconciliation.total_ledger_credits}
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Discrepancies</div>
                  <div className="mono" style={{ fontSize: '1.25rem', fontWeight: '800', color: reconciliation.transfer_discrepancies_count === 0 ? '#10b981' : '#f43f5e', marginTop: '0.25rem' }}>
                    {reconciliation.transfer_discrepancies_count}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Concurrency Engine Lab */}
        {activeAdminTab === 'concurrency' && (
          <div style={{ marginTop: '0.5rem' }}>
            <ConcurrencyDemo userAccounts={userAccounts} onRefresh={onRefresh} />
          </div>
        )}
      </div>
    </div>
  );
};
