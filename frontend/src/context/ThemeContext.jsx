import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const KEY = 'accessai.appearance';
const DEFAULTS = { theme: 'system', fontScale: 1, reduceMotion: false };
const ThemeCtx = createContext(null);

const load = () => {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; } catch { return DEFAULTS; }
};

const resolve = (theme) =>
  theme === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;

export function ThemeProvider({ children }) {
  const [prefs, setPrefs] = useState(load);

  useEffect(() => {
    const apply = () => {
      const root = document.documentElement;
      root.dataset.theme = resolve(prefs.theme);
      root.dataset.motion = prefs.reduceMotion ? 'reduce' : 'full';
      root.style.setProperty('--font-scale', prefs.fontScale);
    };
    apply();
    localStorage.setItem(KEY, JSON.stringify(prefs));
    if (prefs.theme !== 'system') return undefined;
    const mq = matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, [prefs]);

  const setTheme = useCallback((theme) => setPrefs((p) => ({ ...p, theme })), []);
  const setFontScale = useCallback((fontScale) => setPrefs((p) => ({ ...p, fontScale })), []);
  const setReduceMotion = useCallback((reduceMotion) => setPrefs((p) => ({ ...p, reduceMotion })), []);

  const value = useMemo(
    () => ({ ...prefs, setTheme, setFontScale, setReduceMotion }),
    [prefs, setTheme, setFontScale, setReduceMotion],
  );
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export const useTheme = () => useContext(ThemeCtx);
