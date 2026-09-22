/**
 * BrandingPanel — Admin-only UI to configure white-label bank settings.
 *
 * Calls PATCH /api/v1/config/branding and uses BrandingContext.updateBranding()
 * to apply changes to CSS variables immediately (no page reload needed).
 */
import React, { useState } from 'react';
import { Palette, Save, RotateCcw, CheckCircle, AlertCircle } from 'lucide-react';
import { useBranding } from '../context/BrandingContext';
import apiClient from '../api/client';

const FIELD_DEFS = [
  { key: 'bank_name',       label: 'Bank Name',        type: 'text',  placeholder: 'e.g. Sunrise Community Bank' },
  { key: 'bank_tagline',    label: 'Tagline',           type: 'text',  placeholder: 'e.g. Your Trusted Financial Partner' },
  { key: 'bank_logo_url',   label: 'Logo URL',          type: 'url',   placeholder: 'https://...' },
  { key: 'primary_color',   label: 'Primary Color',     type: 'color', placeholder: '#2563eb' },
  { key: 'secondary_color', label: 'Secondary Color',   type: 'color', placeholder: '#1e40af' },
  { key: 'accent_color',    label: 'Accent Color',      type: 'color', placeholder: '#3b82f6' },
  { key: 'support_email',   label: 'Support Email',     type: 'email', placeholder: 'support@bank.com' },
  { key: 'support_phone',   label: 'Support Phone',     type: 'text',  placeholder: '+1-800-000-0000' },
  { key: 'bank_country',    label: 'Country',           type: 'text',  placeholder: 'US' },
  { key: 'currency_code',   label: 'Currency Code',     type: 'text',  placeholder: 'USD' },
  { key: 'currency_symbol', label: 'Currency Symbol',   type: 'text',  placeholder: '$' },
  { key: 'routing_number',  label: 'Routing Number',    type: 'text',  placeholder: '021000021' },
  { key: 'swift_code',      label: 'SWIFT Code',        type: 'text',  placeholder: 'CHASUS33' },
];

export const BrandingPanel = () => {
  const { branding, updateBranding } = useBranding();

  const [form, setForm] = useState(() => {
    const init = {};
    FIELD_DEFS.forEach(f => { init[f.key] = branding[f.key] || ''; });
    return init;
  });
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null); // { ok: bool, message: str }

  const handleChange = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }));
    // Apply color changes to CSS immediately for live preview
    if (key === 'primary_color')   document.documentElement.style.setProperty('--brand-primary',   value);
    if (key === 'secondary_color') document.documentElement.style.setProperty('--brand-secondary', value);
    if (key === 'accent_color')    document.documentElement.style.setProperty('--brand-accent',    value);
  };

  const handleReset = () => {
    const reset = {};
    FIELD_DEFS.forEach(f => { reset[f.key] = branding[f.key] || ''; });
    setForm(reset);
    setResult(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setResult(null);
    try {
      // Only send non-empty fields
      const payload = {};
      FIELD_DEFS.forEach(({ key }) => { if (form[key]) payload[key] = form[key]; });

      const res = await apiClient.patch('/config/branding', payload);
      updateBranding(res.data.branding);
      setResult({ ok: true, message: 'Branding saved and applied live.' });
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Save failed.';
      setResult({ ok: false, message: msg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <div style={{ background: 'rgba(139, 92, 246, 0.15)', padding: '0.625rem', borderRadius: '10px', color: '#a78bfa' }}>
          <Palette size={20} />
        </div>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: '700', color: '#ffffff' }}>White-Label Branding</h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Color changes apply instantly as a live preview. Save to persist to database.
          </p>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '1rem',
        marginBottom: '1.25rem'
      }}>
        {FIELD_DEFS.map(({ key, label, type, placeholder }) => (
          <div key={key} className="input-group" style={{ marginBottom: 0 }}>
            <label className="input-label">{label}</label>
            {type === 'color' ? (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  type="color"
                  value={form[key] || '#2563eb'}
                  onChange={e => handleChange(key, e.target.value)}
                  style={{ width: 40, height: 38, border: 'none', borderRadius: 8, cursor: 'pointer', background: 'none' }}
                />
                <input
                  type="text"
                  className="input-field"
                  value={form[key]}
                  onChange={e => handleChange(key, e.target.value)}
                  placeholder={placeholder}
                  style={{ flex: 1 }}
                />
              </div>
            ) : (
              <input
                type={type}
                className="input-field"
                value={form[key]}
                onChange={e => handleChange(key, e.target.value)}
                placeholder={placeholder}
              />
            )}
          </div>
        ))}
      </div>

      {result && (
        <div className={`alert ${result.ok ? 'alert-success' : 'alert-error'}`} style={{ marginBottom: '1rem' }}>
          {result.ok ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {result.message}
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
        <button className="btn btn-secondary" onClick={handleReset} disabled={saving}>
          <RotateCcw size={15} /> Reset
        </button>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          <Save size={15} /> {saving ? 'Saving…' : 'Save Branding'}
        </button>
      </div>
    </div>
  );
};

