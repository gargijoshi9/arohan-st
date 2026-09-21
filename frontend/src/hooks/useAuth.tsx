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
  loginApplicant: (name: string, email: string) => void;
  loginAdmin: (name?: string) => void;
  logout: () => void;
  selectDemoProfile: (profileKey: 'ramesh' | 'sunita' | 'amit' | 'officer') => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEMO_PROFILES: Record<string, UserProfile> = {
  ramesh: {
    role: 'applicant',
    name: 'Ramesh Chandra Munda',
    email: 'ramesh.munda@example.edu',
    category: 'ST'
  },
  sunita: {
    role: 'applicant',
    name: 'Sunita Devi Soren',
    email: 'sunita.soren@example.com',
    category: 'ST'
  },
  amit: {
    role: 'applicant',
    name: 'Amit Tirkey',
    email: 'amit.tirkey@example.com',
    category: 'ST'
  },
  officer: {
    role: 'admin',
    name: 'Dr. Arjun K. Meena',
    email: 'arjun.meena@tribal.gov.in',
    officerDesignation: 'Director (Scholarship & Fellowship Cell), MoTA'
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    // Default to applicant Ramesh or read from localStorage
    const saved = localStorage.getItem('arohan_auth_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // fallback
      }
    }
    return DEMO_PROFILES.ramesh;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('arohan_auth_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('arohan_auth_user');
    }
  }, [user]);

  const loginApplicant = (name: string, email: string) => {
    setUser({
      role: 'applicant',
      name: name || 'ST Scholar',
      email: email || 'scholar@example.edu',
      category: 'ST'
    });
  };

  const loginAdmin = (name: string = 'MoTA Verification Officer') => {
    setUser({
      role: 'admin',
      name,
      email: 'officer@tribal.gov.in',
      officerDesignation: 'Verification Officer (MoTA Desk)'
    });
  };

  const logout = () => {
    setUser(null);
  };

  const selectDemoProfile = (profileKey: 'ramesh' | 'sunita' | 'amit' | 'officer') => {
    if (DEMO_PROFILES[profileKey]) {
      setUser(DEMO_PROFILES[profileKey]);
    }
  };

  const isAdmin = user?.role === 'admin';
  const isApplicant = user?.role === 'applicant';

  return (
    <AuthContext.Provider
      value={{
        user,
        isAdmin,
        isApplicant,
        loginApplicant,
        loginAdmin,
        logout,
        selectDemoProfile
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
