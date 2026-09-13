import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { accountApi, transferApi } from '../api/client';
import { Navbar } from '../components/Navbar';
import { AccountCard } from '../components/AccountCard';
import { TransferModal } from '../components/TransferModal';
import { DepositModal } from '../components/DepositModal';
import { CreateAccountModal } from '../components/CreateAccountModal';
import { TransactionTable } from '../components/TransactionTable';
import { ConcurrencyDemo } from '../components/ConcurrencyDemo';
import { AdminPanel } from '../components/AdminPanel';
import { Plus, ArrowUpRight, ShieldCheck, Wallet } from 'lucide-react';

export const DashboardPage = () => {
  const { user, isAdmin, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, per_page: 10, total_items: 0, total_pages: 0 });
  const [filters, setFilters] = useState({ type: 'ALL', status: '', page: 1, per_page: 10 });
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingTx, setLoadingTx] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [isTransferOpen, setIsTransferOpen] = useState(false);
  const [isDepositOpen, setIsDepositOpen] = useState(false);
  const [isCreateAccountOpen, setIsCreateAccountOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await accountApi.list();
      setAccounts(res.data.accounts || []);
      return res.data.accounts;
    } catch (err) {
      console.error('Error fetching accounts:', err);
      return [];
    } finally {
      setLoadingAccounts(false);
    }
  }, []);

  const fetchTransactions = useCallback(async (currentFilters = filters) => {
    setLoadingTx(true);
    try {
      const params = {
        page: currentFilters.page,
        per_page: currentFilters.per_page,
        status: currentFilters.status || undefined,
        type: currentFilters.type !== 'ALL' ? currentFilters.type : undefined
      };
      const res = await transferApi.getHistory(params);
      setTransactions(res.data.transactions || []);
      setPagination(res.data.pagination || { page: 1, per_page: 10, total_items: 0, total_pages: 0 });
    } catch (err) {
      console.error('Error fetching transaction ledger:', err);
    } finally {
      setLoadingTx(false);
    }
  }, [filters]);

  const handleFullRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchAccounts(), fetchTransactions(filters), refreshUser()]);
    setRefreshing(false);
  };

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  useEffect(() => {
    fetchTransactions(filters);
  }, [filters, fetchTransactions]);

  const handleOpenTransfer = (account) => {
    setSelectedAccount(account || accounts[0]);
    setIsTransferOpen(true);
  };

  const handleOpenDeposit = (account) => {
    setSelectedAccount(account || accounts[0]);
    setIsDepositOpen(true);
  };

  const totalBalance = accounts.reduce((sum, acc) => sum + parseFloat(acc.balance || 0), 0);
  const formattedTotal = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(totalBalance);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', paddingBottom: '4rem' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefresh={handleFullRefresh}
        refreshing={refreshing}
      />

      <main className="container" style={{ marginTop: '2rem' }}>
        {activeTab === 'overview' && (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '1.25rem',
              marginBottom: '2rem'
            }}>
              <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                <div style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '0.875rem', borderRadius: '12px', color: '#3b82f6' }}>
                  <Wallet size={28} />
                </div>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Total Liquidity Balance</div>
                  <div className="mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: '#ffffff', letterSpacing: '-0.02em' }}>
                    {formattedTotal}
                  </div>
                </div>
              </div>

              <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '0.875rem', borderRadius: '12px', color: '#10b981' }}>
                  <ShieldCheck size={28} />
                </div>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Active Bank Accounts</div>
                  <div className="mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: '#ffffff' }}>
                    {accounts.length}
                  </div>
                </div>
              </div>

              <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                <div style={{ background: 'rgba(139, 92, 246, 0.15)', padding: '0.875rem', borderRadius: '12px', color: '#8b5cf6' }}>
                  <ArrowUpRight size={28} />
                </div>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>Ledger Transactions</div>
                  <div className="mono" style={{ fontSize: '1.75rem', fontWeight: '800', color: '#ffffff' }}>
                    {pagination.total_items}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#ffffff' }}>Your Bank Accounts</h2>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  Multi-account balances protected with row-level transaction safety.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => setIsCreateAccountOpen(true)}
                  style={{ padding: '0.55rem 1rem' }}
                >
                  <Plus size={16} /> Open New Account
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => handleOpenTransfer(accounts[0])}
                  disabled={accounts.length === 0}
                  style={{ padding: '0.55rem 1.15rem' }}
                >
                  <ArrowUpRight size={16} /> Send Transfer
                </button>
              </div>
            </div>

            {loadingAccounts ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading bank accounts...
              </div>
            ) : accounts.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>No accounts found.</p>
                <button className="btn btn-primary" onClick={() => setIsCreateAccountOpen(true)}>
                  <Plus size={16} /> Provision Primary Account
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
                {accounts.map((acc) => (
                  <AccountCard
                    key={acc.account_id}
                    account={acc}
                    onSend={handleOpenTransfer}
                    onDeposit={handleOpenDeposit}
                  />
                ))}
              </div>
            )}

            <TransactionTable
              transactions={transactions}
              pagination={pagination}
              userAccounts={accounts}
              loading={loadingTx}
              filters={filters}
              onFilterChange={(newFilters) => setFilters(newFilters)}
              onPageChange={(newPage) => setFilters(prev => ({ ...prev, page: newPage }))}
            />
          </>
        )}

        {activeTab === 'concurrency' && (
          <ConcurrencyDemo
            userAccounts={accounts}
            onRefresh={handleFullRefresh}
          />
        )}

        {activeTab === 'admin' && isAdmin && (
          <AdminPanel
            userAccounts={accounts}
            onRefresh={handleFullRefresh}
          />
        )}
      </main>

      <TransferModal
        isOpen={isTransferOpen}
        onClose={() => setIsTransferOpen(false)}
        userAccounts={accounts}
        preselectedAccount={selectedAccount}
        onSuccess={handleFullRefresh}
      />

      <DepositModal
        isOpen={isDepositOpen}
        onClose={() => setIsDepositOpen(false)}
        account={selectedAccount}
        onSuccess={handleFullRefresh}
      />

      <CreateAccountModal
        isOpen={isCreateAccountOpen}
        onClose={() => setIsCreateAccountOpen(false)}
        onSuccess={handleFullRefresh}
      />
    </div>
  );
};
