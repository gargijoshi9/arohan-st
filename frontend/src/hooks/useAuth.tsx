import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';

export type UserRole = 'applicant' | 'admin' | null;

export interface UserProfile {
  role: UserRole;
  name: string;
  email: string;
  category?: string;
  officerDesignation?: string;
}

interface AuthContextType {
  user: UserProfile | null;
  isAdmin: boolean;
  isApplicant: boolean;
  loginPortal: (name: string, email: string, secret?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const USER_KEY = 'arohan_auth_user_v3';
const ADMIN_EMAIL = 'motaofficer@gmail.com';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    if (!localStorage.getItem('arohan_access_token_v1')) return null;
    try {
      const saved = localStorage.getItem(USER_KEY);
      return saved ? JSON.parse(saved) as UserProfile : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  }, [user]);

  const loginPortal = async (name: string, email: string, secret = '') => {
    const isAdmin = email.trim().toLowerCase() === ADMIN_EMAIL;
    const result = await api.login({
      role: isAdmin ? 'admin' : 'applicant',
      email: email.trim(),
      name: name.trim(),
      ...(isAdmin ? { password: secret } : { otp: secret })
    });
    api.saveToken(result.access_token);
    setUser({
      role: result.role,
      name: result.name,
      email: result.email,
      category: result.role === 'applicant' ? 'ST' : undefined,
      officerDesignation: result.role === 'admin' ? 'Verification Officer (MoTA Desk)' : undefined
    });
  };

  const logout = () => {
    api.clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAdmin: user?.role === 'admin',
        isApplicant: user?.role === 'applicant',
        loginPortal,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
