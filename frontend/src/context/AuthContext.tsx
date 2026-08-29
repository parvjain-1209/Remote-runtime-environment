import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  fetchCurrentUser,
  getStoredToken,
  loginUser,
  registerUser,
  removeStoredToken,
} from '../services/api';
import { LoginRequest, RegisterRequest, User } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (req: LoginRequest) => Promise<void>;
  register: (req: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredToken();
      if (token) {
        try {
          const userData = await fetchCurrentUser();
          setUser(userData);
        } catch {
          removeStoredToken();
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (req: LoginRequest) => {
    const tokenResp = await loginUser(req);
    setUser(tokenResp.user);
  };

  const register = async (req: RegisterRequest) => {
    const tokenResp = await registerUser(req);
    setUser(tokenResp.user);
  };

  const logout = () => {
    removeStoredToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
