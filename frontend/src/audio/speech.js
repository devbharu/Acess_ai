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
    set(null, 'idle');
  },
  async speak(key, text, opts) {
    if (current.key === key) return speechStore.stop();
    speechStore.stop();
    set(key, 'loading');
    try {
      const cacheKey = `${opts.voice}|${opts.speed}|${text}`;
      let url = cache.get(cacheKey);
      if (!url) {
        url = URL.createObjectURL(await api.tts(text, opts));
        cache.set(cacheKey, url);
        if (cache.size > 30) {
          const oldest = cache.keys().next().value;
          URL.revokeObjectURL(cache.get(oldest));
          cache.delete(oldest);
        }
      }
      if (current.key !== key) return; // cancelled while loading
      audio = new Audio(url);
      audio.onended = () => set(null, 'idle');
      audio.onerror = () => set(null, 'idle');
      await audio.play();
      set(key, 'playing');
    } catch {
      set(null, 'idle');
    }
  },
};
