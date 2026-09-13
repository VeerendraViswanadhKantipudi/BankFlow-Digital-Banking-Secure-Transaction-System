import axios from 'axios';

// Base URL for the BankFlow Flask REST API
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';

// Shared Axios HTTP client instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request Interceptor: Automatically attaches JWT bearer token from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('bankflow_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response Interceptor: Intercepts 401 Unauthorized errors (expired/invalid JWT)
// Clears stored session state and triggers an auth_logout custom event for automatic logout
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (localStorage.getItem('bankflow_token')) {
        localStorage.removeItem('bankflow_token');
        localStorage.removeItem('bankflow_user');
        window.dispatchEvent(new Event('auth_logout'));
      }
    }
    return Promise.reject(error);
  }
);

// Authentication & Profile Endpoints
export const authApi = {
  login: (credentials) => apiClient.post('/auth/login', credentials),
  register: (data) => apiClient.post('/auth/register', data),
  getMe: () => apiClient.get('/auth/me')
};

export const accountApi = {
  list: () => apiClient.get('/accounts'),
  getById: (id) => apiClient.get(`/accounts/${id}`),
  create: (data) => apiClient.post('/accounts', data),
  deposit: (id, data) => apiClient.post(`/accounts/${id}/deposit`, data),
  updateStatus: (id, status) => apiClient.patch(`/accounts/${id}/status`, { status }),
  updateUserRole: (userId, role) => apiClient.patch(`/accounts/admin/users/${userId}/role`, { role }),
  listAllAdmin: () => apiClient.get('/accounts/admin/users'),
  getAuditLogs: (params) => apiClient.get('/accounts/admin/audit-logs', { params }),
  reconcile: () => apiClient.get('/accounts/admin/reconcile')
};

// Funds Transfer & Transaction History Endpoints
export const transferApi = {
  transfer: (data) => apiClient.post('/transfers', data),
  getHistory: (params) => apiClient.get('/transfers/history', { params })
};

export default apiClient;
