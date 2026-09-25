import React, { createContext, useContext, useState, useEffect } from 'react';

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
  loginPortal: (name: string, email: string, password?: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_ADMIN_USERNAME = 'MotaOfficer@gmail.com';
const DEMO_ADMIN_PASSWORD = 'MotaOfficer';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    // Require the user to choose an applicant or officer login each session.
    const saved = localStorage.getItem('arohan_auth_user_v2');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // fallback
      }
    }
    return null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('arohan_auth_user_v2', JSON.stringify(user));
    } else {
      localStorage.removeItem('arohan_auth_user_v2');
    }
  }, [user]);

  const loginPortal = (name: string, email: string, password = ''): boolean => {
    if (email.trim().toLowerCase() === DEMO_ADMIN_USERNAME.toLowerCase()) {
      if (password !== DEMO_ADMIN_PASSWORD) return false;
      setUser({
        role: 'admin',
        name: name.trim() || 'MoTA Officer',
        email: DEMO_ADMIN_USERNAME,
        officerDesignation: 'Verification Officer (MoTA Desk)'
      });
      return true;
    }
    setUser({
      role: 'applicant',
      name: name || 'ST Scholar',
      email: email || 'scholar@example.edu',
      category: 'ST'
    });
    return true;
  };

  const logout = () => {
    setUser(null);
  };

  const isAdmin = user?.role === 'admin';
  const isApplicant = user?.role === 'applicant';

  return (
    <AuthContext.Provider
      value={{
        user,
        isAdmin,
        isApplicant,
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
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
