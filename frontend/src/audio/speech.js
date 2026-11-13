import { api } from '../api/client';

// Tiny external store so every "Listen" button shares one audio element.
const listeners = new Set();
const cache = new Map();
let audio = null;
let current = { key: null, state: 'idle' };

const emit = () => listeners.forEach((l) => l());
const set = (key, state) => { current = { key: state === 'idle' ? null : key, state }; emit(); };

export const speechStore = {
  subscribe(l) { listeners.add(l); return () => listeners.delete(l); },
  stateFor: (key) => (current.key === key ? current.state : 'idle'),
  stop() {
    if (audio) { audio.pause(); audio.src = ''; audio = null; }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try { window.speechSynthesis.cancel(); } catch {}
    }
    set(null, 'idle');
  },
  async speak(key, text, opts = {}) {
    if (current.key === key) return speechStore.stop();
    speechStore.stop();
    set(key, 'loading');

    // 1. Try high-fidelity backend audio stream
    try {
      const cacheKey = `${opts.voice}|${opts.speed}|${text}`;
      let url = cache.get(cacheKey);
      if (!url) {
        const blob = await api.tts(text, opts);
        url = URL.createObjectURL(blob);
        cache.set(cacheKey, url);
        if (cache.size > 30) {
          const oldest = cache.keys().next().value;
          URL.revokeObjectURL(cache.get(oldest));
          cache.delete(oldest);
        }
      }
      if (current.key !== key) return;
      audio = new Audio(url);
      audio.onended = () => set(null, 'idle');
      audio.onerror = () => fallbackBrowserSpeech(key, text, opts);
      await audio.play();
      set(key, 'playing');
      return;
    } catch {
      // 2. Fall back to browser Web Speech API (offline / deployed network fallback)
      fallbackBrowserSpeech(key, text, opts);
    }
  },
};

function fallbackBrowserSpeech(key, text, opts) {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      if (opts?.speed) utterance.rate = Math.max(0.6, Math.min(1.8, Number(opts.speed)));
      utterance.onend = () => set(null, 'idle');
      utterance.onerror = () => set(null, 'idle');
      window.speechSynthesis.speak(utterance);
      set(key, 'playing');
      return;
    } catch {
      set(null, 'idle');
    }
  } else {
    set(null, 'idle');
  }
}
