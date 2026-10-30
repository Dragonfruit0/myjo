/*
 * Auth context: who is signed in, which screens and action permissions they have.
 * `screens` and `perms` come from GET /auth/me and drive the menu and the buttons that need a perm.
 * Record-level buttons use each record's `actions` array instead.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { get, getSession, onUnauthorized, post, setSession } from './api';
import type { LoginResponse, MeResponse, PermCode, Role, ScreenCode, User } from './types';

type Status = 'loading' | 'out' | 'setup' | 'in';

export type Secret = { password: string } | { pin: string };

interface AuthValue {
  status: Status;
  user: User | null;
  screens: ScreenCode[];
  perms: PermCode[];
  /** Shown on the sign-in page after an expired session or sign-out. */
  notice: string | null;
  lastRole: Role | null;
  login: (role: Role, username: string, secret: Secret) => Promise<void>;
  setup: (password: string, pin: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  can: (p: PermCode) => boolean;
  sees: (s: ScreenCode) => boolean;
}

const AuthContext = createContext<AuthValue | null>(null);

interface State {
  status: Status;
  user: User | null;
  screens: ScreenCode[];
  perms: PermCode[];
}

const SIGNED_OUT: State = { status: 'out', user: null, screens: [], perms: [] };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>(() => (getSession() ? { ...SIGNED_OUT, status: 'loading' } : SIGNED_OUT));
  const [notice, setNotice] = useState<string | null>(null);
  const [lastRole, setLastRole] = useState<Role | null>(null);

  const loadMe = useCallback(async () => {
    const me = await get<MeResponse>('/auth/me');
    const mustChange = getSession()?.must_change === true;
    setState({ status: mustChange ? 'setup' : 'in', user: me.user, screens: me.screens ?? [], perms: me.perms ?? [] });
  }, []);

  useEffect(() => {
    onUnauthorized(() => {
      setState(SIGNED_OUT);
      setNotice('Your session has ended. Please sign in again.');
    });
    if (getSession()) {
      loadMe().catch(() => {
        setSession(null);
        setState(SIGNED_OUT);
      });
    }
    return () => onUnauthorized(null);
  }, [loadMe]);

  const login = useCallback(
    async (role: Role, username: string, secret: Secret) => {
      const res = await post<LoginResponse>('/auth/login', { role, username, ...secret });
      setSession({ token: res.token, must_change: res.must_change });
      setNotice(null);
      setLastRole(role);
      if (res.must_change) setState({ status: 'setup', user: res.user, screens: [], perms: [] });
      else await loadMe();
    },
    [loadMe],
  );

  const setup = useCallback(
    async (password: string, pin: string) => {
      const res = await post<LoginResponse>('/auth/setup', { password, pin });
      setSession({ token: res.token, must_change: false });
      await loadMe();
    },
    [loadMe],
  );

  const logout = useCallback(async () => {
    const role = state.user?.role ?? null;
    try {
      await post('/auth/logout');
    } catch {
      /* signing out locally is enough */
    }
    setSession(null);
    setLastRole(role);
    setNotice(null);
    setState(SIGNED_OUT);
  }, [state.user]);

  const value = useMemo<AuthValue>(
    () => ({
      ...state,
      notice,
      lastRole,
      login,
      setup,
      logout,
      refresh: loadMe,
      can: (p) => state.perms.includes(p),
      sees: (s) => state.screens.includes(s),
    }),
    [state, notice, lastRole, login, setup, logout, loadMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(AuthContext);
  if (!v) throw new Error('useAuth must be used inside <AuthProvider>');
  return v;
}

/** For screens rendered inside the signed-in shell, where a user always exists. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error('No signed-in user');
  return user;
}
