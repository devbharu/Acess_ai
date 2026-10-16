import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import AppShell from './components/AppShell';
import { useAuth } from './context/AuthContext';

const Login = lazy(() => import('./pages/Login'));
const Chat = lazy(() => import('./pages/Chat'));
const Settings = lazy(() => import('./pages/Settings'));
const Metrics = lazy(() => import('./pages/Metrics'));

const Loading = () => (
  <div style={{ display: 'grid', placeItems: 'center', height: '100dvh' }} role="status" aria-label="Loading">
    <Loader2 className="spin" size={32} />
  </div>
);

function Protected() {
  const { status } = useAuth();
  if (status === 'loading') return <Loading />;
  if (status === 'anon') return <Navigate to="/login" replace />;
  return <AppShell />;
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<Protected />}>
          <Route path="/chat" element={<Chat />} />
          <Route path="/chat/:id" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/metrics" element={<Metrics />} />
        </Route>

        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Suspense>
  );
}
