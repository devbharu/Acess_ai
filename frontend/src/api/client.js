const BASE = (import.meta.env.VITE_API_URL || '') + '/api';
const TOKEN_KEY = 'accessai.token';

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function request(path, { method = 'GET', json, form, raw, signal } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  if (form) body = form;

  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body, signal });
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new Error('Cannot reach the server. Is the backend running?');
  }
  if (res.status === 401 && token) onUnauthorized();
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try { msg = (await res.json()).error || msg; } catch { /* non-JSON error */ }
    throw new Error(msg);
  }
  if (raw) return res;
  return res.status === 204 ? null : res.json();
}

const upload = (path, file, extra = {}) => {
  const form = new FormData();
  form.append('file', file);
  Object.entries(extra).forEach(([k, v]) => v != null && form.append(k, v));
  return request(path, { method: 'POST', form });
};

export const api = {
  login: (email, password) => request('/auth/login', { method: 'POST', json: { email, password } }),
  register: (name, email, password) => request('/auth/register', { method: 'POST', json: { name, email, password } }),
  me: () => request('/auth/me'),
  updateProfile: (patch) => request('/auth/me', { method: 'PUT', json: patch }),

  getSettings: () => request('/settings'),
  saveSettings: (patch) => request('/settings', { method: 'PUT', json: patch }),

  listConversations: () => request('/conversations'),
  getMessages: (id) => request(`/conversations/${id}/messages`),
  getConversationAttachments: (id) => request(`/conversations/${id}/attachments`),
  getConversationArtifacts: (id) => request(`/conversations/${id}/artifacts`),
  renameConversation: (id, title) => request(`/conversations/${id}`, { method: 'PUT', json: { title } }),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: 'DELETE' }),

  uploadDocument: (file, conversationId) => upload('/documents', file, { conversation_id: conversationId }),
  uploadImage: (file, conversationId) => upload('/images', file, { conversation_id: conversationId }),

  stt: (blob, { language, model } = {}) => upload('/stt', new File([blob], 'voice.webm', { type: blob.type }), { language, model }),
  tts: async (text, { voice, speed } = {}) => {
    const res = await request('/tts', { method: 'POST', json: { text, voice, speed }, raw: true });
    return res.blob();
  },

  getMetrics: () => request('/metrics'),
  runEvaluation: (suite) => request('/metrics/run', { method: 'POST', json: { suite } }),
};

/** POST /chat and parse the server-sent events stream. */
export async function streamChat(payload, handlers, signal) {
  const res = await request('/chat', { method: 'POST', json: payload, raw: true, signal });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = 'message';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
      }
      if (!data) continue;
      try { handlers[event]?.(JSON.parse(data)); } catch { /* ignore malformed event */ }
    }
  }
}
