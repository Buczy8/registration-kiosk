import React, { createContext, useState, useEffect, useContext } from 'react';
import { login as apiLogin, register as apiRegister, getProfile } from '../api/auth.js';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => sessionStorage.getItem('kiosk_token') || null);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(!!token);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const initSession = async () => {
      if (token) {
        try {
          const profile = await getProfile(token);
          setUser(profile);
          setIsAuthenticated(true);
        } catch (error) {
          console.error("Błąd przywracania sesji:", error);
          logout();
        }
      }
      setIsInitializing(false);
    };

    initSession();
  }, [token]);

  const login = async (payload) => {
    const response = await apiLogin(payload);
    const accessToken = response.access_token;

    sessionStorage.setItem('kiosk_token', accessToken);
    setToken(accessToken);

    const profile = await getProfile(accessToken);
    setUser(profile);
    setIsAuthenticated(true);
  };

  const register = async (payload) => {
    await apiRegister(payload);
    await login({ email: payload.email, password: payload.password });
  };

  const logout = () => {
    sessionStorage.removeItem('kiosk_token');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{
      token,
      user,
      isAuthenticated,
      isInitializing,
      login,
      register,
      logout
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);