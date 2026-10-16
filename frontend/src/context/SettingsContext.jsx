import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import { DEFAULT_SETTINGS } from '../config/models';
import { useAuth } from './AuthContext';

const SettingsCtx = createContext(null);

export function SettingsProvider({ children }) {
  const { user } = useAuth();
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [status, setStatus] = useState('idle'); // idle | saving | saved | error
  const pending = useRef({});
  const timer = useRef(null);

  const flush = useCallback(async () => {
    const patch = pending.current;
    pending.current = {};
    if (!Object.keys(patch).length) return;
    setStatus('saving');
    try { await api.saveSettings(patch); setStatus('saved'); } catch { setStatus('error'); }
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    let off = false;
    api.getSettings().then((s) => !off && setSettings({ ...DEFAULT_SETTINGS, ...s })).catch(() => {});
    return () => { off = true; clearTimeout(timer.current); flush(); };
  }, [user?.id, flush]); // eslint-disable-line react-hooks/exhaustive-deps

  const update = useCallback((patch) => {
    setSettings((s) => ({ ...s, ...patch }));
    pending.current = { ...pending.current, ...patch };
    clearTimeout(timer.current);
    timer.current = setTimeout(flush, 500);
  }, [flush]);

  const reset = useCallback(() => update({ ...DEFAULT_SETTINGS }), [update]);

  const value = useMemo(() => ({ settings, status, update, reset }), [settings, status, update, reset]);
  return <SettingsCtx.Provider value={value}>{children}</SettingsCtx.Provider>;
}

export const useSettings = () => useContext(SettingsCtx);
