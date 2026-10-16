import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Eye, FileText, Loader2, Mic, Volume2 } from 'lucide-react';
import { Brand } from '../components/AppShell';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { status, login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (status === 'authed') return <Navigate to="/chat" replace />;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') await login(form.email, form.password);
      else await register(form.name, form.email, form.password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const isLogin = mode === 'login';
  return (
    <div className="login">
      <section className="login-hero" aria-label="About AccessAI">
        <div className="login-orb" aria-hidden />
        <Brand />
        <div style={{ position: 'relative' }}>
          <h1>Hear your<br />documents.<br /><em>Ask anything.</em></h1>
          <p>One assistant that reads scanned pages, describes images, listens to your questions and answers out loud, using only what is actually in your files.</p>
        </div>
        <div className="feature-row">
          <span><FileText size={16} /> OCR</span>
          <span><Eye size={16} /> Image understanding</span>
          <span><Mic size={16} /> Voice input</span>
          <span><Volume2 size={16} /> Spoken answers</span>
        </div>
      </section>
      <main className="login-panel" id="main" tabIndex={-1}>
        <div className="login-form">
          <div>
            <h2>{isLogin ? 'Welcome back' : 'Create your account'}</h2>
            <p className="hint" style={{ marginTop: 8 }}>{isLogin ? 'Sign in to continue your conversations.' : 'It takes less than a minute.'}</p>
          </div>
          <form onSubmit={onSubmit} noValidate={false}>
            {!isLogin && (
              <div className="field">
                <label htmlFor="name">Name</label>
                <input id="name" className="input" required autoComplete="name" value={form.name} onChange={set('name')} />
              </div>
            )}
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" className="input" required autoComplete="email" value={form.email} onChange={set('email')} />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" type="password" className="input" required minLength={isLogin ? 1 : 8}
                autoComplete={isLogin ? 'current-password' : 'new-password'} value={form.password} onChange={set('password')}
                aria-describedby={!isLogin ? 'pw-hint' : undefined} />
              {!isLogin && <p id="pw-hint" className="hint">At least 8 characters.</p>}
            </div>
            <p className="error-text" role="alert" aria-live="assertive">{error}</p>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ minHeight: 52 }}>
              {loading && <Loader2 size={18} className="spin" />} {isLogin ? 'Sign in' : 'Create account'}
            </button>
          </form>
          <p className="login-switch">
            {isLogin ? 'New here?' : 'Already have an account?'}{' '}
            <button type="button" onClick={() => { setMode(isLogin ? 'register' : 'login'); setError(''); }}>
              {isLogin ? 'Create an account' : 'Sign in'}
            </button>
          </p>
        </div>
      </main>
    </div>
  );
}
