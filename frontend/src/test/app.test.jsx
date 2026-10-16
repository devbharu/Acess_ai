import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';
import { AuthProvider } from '../context/AuthContext';
import { ChatProvider } from '../context/ChatContext';
import { SettingsProvider } from '../context/SettingsContext';
import { ThemeProvider } from '../context/ThemeContext';

const USER = { id: 'u1', name: 'Bharath', email: 'b@example.com' };
const METRICS = {
  summary: { answer_correctness: 87.4, wer: 8.1, ocr_accuracy: 94.2, faithfulness: 91, hallucination_rate: 4.3, retrieval_hit: 93.5, latency_p50: 3.4, latency_p95: 7.9 },
  history: [{ label: 'R1', answer_correctness: 80, ocr_accuracy: 90 }, { label: 'R2', answer_correctness: 87, ocr_accuracy: 94 }],
  robustness: [{ label: 'Clean', value: 91 }, { label: 'Noisy speech', value: 82 }],
  latency: [{ label: 'LLM', value: 2.6 }, { label: 'OCR', value: 1.2 }],
  runs: [],
};

const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } });
const sse = (events) => {
  const enc = new TextEncoder();
  return new Response(new ReadableStream({
    start(c) { events.forEach(([e, d]) => c.enqueue(enc.encode(`event: ${e}\ndata: ${JSON.stringify(d)}\n\n`))); c.close(); },
  }), { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
};

function mockApi() {
  globalThis.fetch = vi.fn(async (url, opts = {}) => {
    const path = String(url).replace('/api', '');
    const method = opts.method || 'GET';
    if (path === '/auth/login') return json({ token: 't', user: USER });
    if (path === '/auth/me') return json(USER);
    if (path === '/settings') return json(method === 'GET' ? {} : {});
    if (path === '/conversations') return json([]);
    if (path === '/metrics') return json(METRICS);
    if (path === '/chat') return sse([
      ['meta', { conversation_id: 'c1' }],
      ['token', { text: 'The total is ' }], ['token', { text: '42,500.' }],
      ['sources', [{ type: 'ocr', source: 'invoice.pdf', page: 1, score: 0.9, text: 'Total: 42,500' }]],
      ['done', { latency_ms: 1500, model: 'gemma4:31b-cloud' }],
    ]);
    return json({});
  });
}

const renderApp = (route) => render(
  <MemoryRouter initialEntries={[route]}>
    <ThemeProvider><AuthProvider><SettingsProvider><ChatProvider><App /></ChatProvider></SettingsProvider></AuthProvider></ThemeProvider>
  </MemoryRouter>,
);

describe('AccessAI frontend', () => {
  beforeEach(() => {
    localStorage.clear();
    mockApi();
  });

  it('redirects anonymous users to login and signs in', async () => {
    renderApp('/chat');
    expect(await screen.findByRole('heading', { name: /welcome back/i })).toBeTruthy();
    await userEvent.type(screen.getByLabelText('Email'), 'b@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'secret123');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText(/what would you like/i)).toBeTruthy();
    expect(localStorage.getItem('accessai.token')).toBe('t');
  });

  it('sends a message and streams the answer with evidence', async () => {
    localStorage.setItem('accessai.token', 't');
    renderApp('/chat');
    const box = await screen.findByLabelText('Message AccessAI');
    await userEvent.type(box, 'What is the amount?');
    await userEvent.click(screen.getByRole('button', { name: 'Send message' }));
    expect(await screen.findByText(/42,500\./)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Read aloud' })).toBeTruthy();
  });

  it('switches settings tabs, selects a model and edits the system prompt', async () => {
    localStorage.setItem('accessai.token', 't');
    renderApp('/settings');
    await userEvent.click(await screen.findByRole('radio', { name: /GPT-OSS 20B/ }));
    expect(screen.getByRole('radio', { name: /GPT-OSS 20B/ }).getAttribute('aria-checked')).toBe('true');
    expect(screen.getByLabelText('Temperature')).toBeTruthy();
    await userEvent.click(screen.getByRole('tab', { name: /System prompt/ }));
    expect(screen.getByRole('textbox', { name: 'System prompt' }).value).toMatch(/AccessAI/);
    await userEvent.click(screen.getByRole('tab', { name: /Appearance/ }));
    await userEvent.click(screen.getByRole('radio', { name: 'High contrast' }));
    expect(document.documentElement.dataset.theme).toBe('contrast');
  });

  it('renders evaluation metrics', async () => {
    localStorage.setItem('accessai.token', 't');
    renderApp('/metrics');
    expect(await screen.findByText('Word error rate')).toBeTruthy();
    await waitFor(() => expect(screen.getByText('87.4')).toBeTruthy());
    expect(screen.getByRole('img', { name: /across evaluation runs/ })).toBeTruthy();
  });
});
