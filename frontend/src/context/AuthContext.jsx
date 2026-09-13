import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('bankflow_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('bankflow_token'));
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      if (localStorage.getItem('bankflow_token')) {
        const res = await authApi.getMe();
        setUser(res.data.user);
        localStorage.setItem('bankflow_user', JSON.stringify(res.data.user));
      }
    } catch (err) {
      console.error('Session validation error:', err);
      logout();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();

    const handleLogoutEvent = () => {
      setUser(null);
      setToken(null);
    };
    window.addEventListener('auth_logout', handleLogoutEvent);
    return () => window.removeEventListener('auth_logout', handleLogoutEvent);
  }, []);

  const login = async (email, password) => {
    const res = await authApi.login({ email, password });
    const { user: authUser, access_token } = res.data.data;
    localStorage.setItem('bankflow_token', access_token);
    localStorage.setItem('bankflow_user', JSON.stringify(authUser));
    setToken(access_token);
    setUser(authUser);
    // Refresh to get accounts
    await fetchProfile();
    return authUser;
  };

  const register = async (formData) => {
    const res = await authApi.register(formData);
    const { user: authUser, access_token } = res.data.data;
    localStorage.setItem('bankflow_token', access_token);
    localStorage.setItem('bankflow_user', JSON.stringify(authUser));
    setToken(access_token);
    setUser(authUser);
    await fetchProfile();
    return authUser;
  };

  const logout = () => {
    localStorage.removeItem('bankflow_token');
    localStorage.removeItem('bankflow_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isAdmin: user?.role === 'ADMIN',
        loading,
        login,
        register,
        logout,
        refreshUser: fetchProfile
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
