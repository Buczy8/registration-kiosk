import { createContext, useState, useEffect, useContext } from 'react';
import { login as apiLogin, logout as apiLogout, register as apiRegister, getProfile } from '../api/auth.js';
import { setUnauthorizedHandler } from '../api/client.js';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const initSession = async () => {
      try {
        const profile = await getProfile();
        setUser(profile);
        setIsAuthenticated(true);
      } catch (error) {
        setUser(null);
        setIsAuthenticated(false);
      } finally {
        setIsInitializing(false);
      }
    };

    initSession();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setUnauthorizedHandler(null);
      return;
    }
    setUnauthorizedHandler(() => {
      logout();
    });
    return () => setUnauthorizedHandler(null);
  }, [isAuthenticated]);

  const login = async (payload) => {
    await apiLogin(payload);
    const profile = await getProfile();
    setUser(profile);
    setIsAuthenticated(true);
    return profile;
  };

  const register = async (payload) => {
    await apiRegister(payload);
    const profile = await getProfile();
    setUser(profile);
    setIsAuthenticated(true);
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch (error) {
      console.error("Błąd wylogowania z serwera:", error);
    } finally {
      // Clear cookie locally on the client (in case HttpOnly is false)
      document.cookie = "kiosk_access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const refreshProfile = async () => {
    try {
      const profile = await getProfile();
      setUser(profile);
      return profile;
    } catch (error) {
      console.error("Błąd odświeżania profilu:", error);
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      isInitializing,
      login,
      register,
      logout,
      refreshProfile
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);