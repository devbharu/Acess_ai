import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, clearToken, getToken, setToken, setUnauthorizedHandler } from '../api/client';

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(getToken() ? 'loading' : 'anon'); // loading | authed | anon

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setStatus('anon');
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!getToken()) return;
    api.me().then((u) => { setUser(u); setStatus('authed'); }).catch(logout);
  }, [logout]);

  const finish = useCallback(({ token, user: u }) => {
    setToken(token);
    setUser(u);
    setStatus('authed');
  }, []);

  const login = useCallback(async (email, password) => finish(await api.login(email, password)), [finish]);
  const register = useCallback(async (name, email, password) => finish(await api.register(name, email, password)), [finish]);
  const updateProfile = useCallback(async (patch) => setUser(await api.updateProfile(patch)), []);

  const value = useMemo(
    () => ({ user, status, login, register, logout, updateProfile }),
    [user, status, login, register, logout, updateProfile],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
