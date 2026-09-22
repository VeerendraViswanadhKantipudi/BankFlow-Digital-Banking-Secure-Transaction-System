/**
 * BrandingContext — white-label theming layer.
 *
 * On mount, fetches GET /api/v1/config/branding and applies the bank's
 * custom colors as CSS custom properties on :root so every component in
 * the tree picks them up via var(--brand-primary) etc. without prop drilling.
 *
 * Falls back to the CSS defaults already set in index.css if the API call
 * fails (network error, cold-start delay, etc.).
 */
import React, { createContext, useContext, useState, useEffect } from 'react';

const BrandingContext = createContext(null);

const DEFAULT_BRANDING = {
  bank_name: 'BankFlow',
  bank_tagline: 'Double-Entry Digital Banking',
  bank_logo_url: '',
  primary_color: '#2563eb',
  secondary_color: '#1e40af',
  accent_color: '#3b82f6',
  support_email: 'support@bankflow.io',
  support_phone: '',
  bank_country: 'US',
  currency_code: 'USD',
  currency_symbol: '$',
  routing_number: '',
  swift_code: '',
};

function applyBrandingToCss(branding) {
  const root = document.documentElement;
  if (branding.primary_color)   root.style.setProperty('--brand-primary',   branding.primary_color);
  if (branding.secondary_color) root.style.setProperty('--brand-secondary', branding.secondary_color);
  if (branding.accent_color)    root.style.setProperty('--brand-accent',    branding.accent_color);
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';

export const BrandingProvider = ({ children }) => {
  const [branding, setBranding] = useState(DEFAULT_BRANDING);
  const [brandingLoading, setBrandingLoading] = useState(true);

  const fetchBranding = async () => {
    try {
      const res = await fetch(`${API_BASE}/config/branding`);
      if (res.ok) {
        const json = await res.json();
        const data = { ...DEFAULT_BRANDING, ...json.branding };
        setBranding(data);
        applyBrandingToCss(data);
      }
    } catch (err) {
      // Network failure — CSS defaults from index.css remain active, no crash
      console.warn('BankFlow: Could not load branding config, using defaults.', err);
    } finally {
      setBrandingLoading(false);
    }
  };

  const updateBranding = (newBranding) => {
    const merged = { ...branding, ...newBranding };
    setBranding(merged);
    applyBrandingToCss(merged);
  };

  useEffect(() => {
    fetchBranding();
  }, []);

  return (
    <BrandingContext.Provider value={{
      branding,
      brandingLoading,
      updateBranding,
      refreshBranding: fetchBranding,
    }}>
      {children}
    </BrandingContext.Provider>
  );
};

export const useBranding = () => {
  const ctx = useContext(BrandingContext);
  if (!ctx) throw new Error('useBranding must be used inside <BrandingProvider>');
  return ctx;
};

