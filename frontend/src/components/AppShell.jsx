import { memo, useCallback, useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, MessageSquare, Menu, LogOut, Plus, Settings, Trash2, Waves, PanelLeftClose, PanelLeftOpen, Paperclip, Image as ImageIcon, FileText } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useChatActions, useChatState } from '../context/ChatContext';

export const Brand = () => (
  <span className="brand">
    <span className="brand-mark" aria-hidden><Waves size={20} strokeWidth={2.6} /></span>
    AccessAI
  </span>
);

const ConversationItem = memo(function ConversationItem({ c, active, onOpen, onDelete }) {
  const attCount = c.attachment_count || 0;
  return (
    <li className={`convo ${active ? 'active' : ''}`}>
      <NavLink to={`/chat/${c.id}`} onClick={onOpen} aria-current={active ? 'page' : undefined} className="convo-link">
        <span className="convo-title">{c.title || 'Untitled'}</span>
        {attCount > 0 && (
          <span className="convo-media-badge" title={`${attCount} file${attCount > 1 ? 's' : ''} attached to this chat`}>
            {c.image_count > 0 && c.doc_count > 0 ? (
              <span className="media-badge-icon"><Paperclip size={11} aria-hidden="true" /> {attCount}</span>
            ) : c.image_count > 0 ? (
              <span className="media-badge-icon"><ImageIcon size={11} aria-hidden="true" /> {c.image_count}</span>
            ) : (
              <span className="media-badge-icon"><FileText size={11} aria-hidden="true" /> {c.doc_count}</span>
            )}
          </span>
        )}
      </NavLink>
      <button type="button" className="icon-btn sm" aria-label={`Delete ${c.title || 'conversation'}`} onClick={() => onDelete(c.id)}><Trash2 size={16} /></button>
    </li>
  );
});

export default function AppShell() {
  const { user, logout } = useAuth();
  const { conversations, activeId } = useChatState();
  const { newChat, deleteConversation } = useChatActions();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('accessai.sidebar_collapsed') === 'true');

  useEffect(() => setOpen(false), [pathname]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('accessai.sidebar_collapsed', String(next));
      return next;
    });
  }, []);

  // Keyboard shortcut Ctrl+\ or Cmd+\ to toggle sidebar
  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === '\\') {
        e.preventDefault();
        toggleCollapsed();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [toggleCollapsed]);

  const onNew = useCallback(() => { newChat(); navigate('/chat'); setOpen(false); }, [newChat, navigate]);
  const onDelete = useCallback(async (id) => {
    if (!window.confirm('Delete this conversation?')) return;
    await deleteConversation(id);
    if (pathname.endsWith(id)) navigate('/chat');
  }, [deleteConversation, navigate, pathname]);
  const close = useCallback(() => setOpen(false), []);

  return (
    <div className={`shell ${collapsed ? 'collapsed' : ''}`}>
      <aside className={`sidebar ${open ? 'open' : ''}`} aria-label="Sidebar">
        <div className="sidebar-top">
          <Brand />
          <button
            type="button"
            className="icon-btn sm"
            onClick={() => {
              if (window.innerWidth <= 860) setOpen(false);
              else toggleCollapsed();
            }}
            aria-label="Collapse sidebar"
            title="Collapse sidebar (Ctrl+\)"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>
        <button type="button" className="btn btn-primary" onClick={onNew}><Plus size={18} /> New conversation</button>
        <nav className="nav" aria-label="Main">
          <NavLink to="/chat"><MessageSquare size={19} /> Assistant</NavLink>
          <NavLink to="/metrics"><BarChart3 size={19} /> Evaluation</NavLink>
          <NavLink to="/settings"><Settings size={19} /> Settings</NavLink>
        </nav>
        <div className="convo-head"><span className="label">Recent</span></div>
        <ul className="convo-list">
          {conversations.map((c) => (
            <ConversationItem key={c.id} c={c} active={c.id === activeId} onOpen={close} onDelete={onDelete} />
          ))}
          {!conversations.length && <li className="hint" style={{ padding: '4px 12px' }}>No conversations yet.</li>}
        </ul>
        <div className="user-chip">
          <span className="avatar" aria-hidden>{(user?.name || '?').slice(0, 1).toUpperCase()}</span>
          <div><strong>{user?.name}</strong><small>{user?.email}</small></div>
          <button type="button" className="icon-btn sm" onClick={logout} aria-label="Sign out" title="Sign out"><LogOut size={18} /></button>
        </div>
      </aside>
      <div className={`scrim ${open ? 'open' : ''}`} onClick={close} aria-hidden />
      <div className={`main ${collapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="mobile-bar">
          <button type="button" className="icon-btn" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={22} /></button>
          <Brand />
        </div>
        {collapsed && (
          <button
            type="button"
            className="icon-btn sidebar-expand-btn"
            onClick={toggleCollapsed}
            aria-label="Expand sidebar"
            title="Expand sidebar (Ctrl+\)"
          >
            <PanelLeftOpen size={20} />
          </button>
        )}
        <main id="main" tabIndex={-1} style={{ display: 'contents' }}><Outlet /></main>
      </div>
    </div>
  );
}
