import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';
import { Profile, RegisterPayload, Session } from '../api/types';

export type { Profile, UserRole } from '../api/types';

interface AuthContextType {
  /** The signed-in account, or null when nobody is signed in. */
  user: Profile | null;
  isAdmin: boolean;
  isApplicant: boolean;
  /** True while the stored session is being revalidated against the API. */
  isRestoring: boolean;
  login: (email: string, password: string) => Promise<Profile>;
  register: (payload: RegisterPayload) => Promise<Profile>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<Profile | null>(null);
  const [isRestoring, setIsRestoring] = useState<boolean>(api.hasToken());

  // A stored token is only trusted after the API confirms it. The role always
  // comes from the server response, never from the email address.
  useEffect(() => {
    let cancelled = false;

    if (!api.hasToken()) {
      setUser(null);
      setIsRestoring(false);
      return;
    }

    api
      .getProfile()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        // Expired or revoked token: drop it so the portal returns to sign-in.
        if (!cancelled) {
          api.clearToken();
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsRestoring(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const establishSession = useCallback(async (session: Session) => {
    api.saveToken(session.access_token);
    const profile = await api.getProfile();
    setUser(profile);
    return profile;
  }, []);

  const login = useCallback(
    async (email: string, password: string) => establishSession(await api.login({ email: email.trim(), password })),
    [establishSession]
  );

  const register = useCallback(
    async (payload: RegisterPayload) =>
      establishSession(
        await api.register({ ...payload, email: payload.email.trim(), full_name: payload.full_name.trim() })
      ),
    [establishSession]
  );

  const logout = useCallback(() => {
    api.clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAdmin: user?.role === 'admin',
        isApplicant: user?.role === 'applicant',
        isRestoring,
        login,
        register,
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
