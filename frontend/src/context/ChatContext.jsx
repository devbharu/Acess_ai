import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, streamChat } from '../api/client';
import { useAuth } from './AuthContext';

// State and actions live in separate contexts so components that only
// dispatch (e.g. the composer buttons) never re-render on every token.
const ChatStateCtx = createContext(null);
const ChatActionsCtx = createContext(null);

let uid = 0;
const nextId = (p) => `${p}-${Date.now()}-${uid++}`;

export function ChatProvider({ children }) {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [media, setMedia] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);
  const activeRef = useRef(null);
  activeRef.current = activeId;

  const refreshConversations = useCallback(async () => {
    try { setConversations(await api.listConversations()); } catch { /* sidebar stays as is */ }
  }, []);

  const refreshMedia = useCallback(async (id) => {
    const targetId = id || activeRef.current;
    if (!targetId) { setMedia([]); return; }
    try { setMedia(await api.getConversationAttachments(targetId)); } catch { setMedia([]); }
  }, []);

  const refreshArtifacts = useCallback(async (id) => {
    const targetId = id || activeRef.current;
    if (!targetId) { setArtifacts([]); return; }
    try {
      const serverArts = await api.getConversationArtifacts(targetId);
      setArtifacts(Array.isArray(serverArts) ? serverArts : []);
    } catch {
      setArtifacts([]);
    }
  }, []);

  useEffect(() => {
    if (user) refreshConversations();
    else { setConversations([]); setMessages([]); setActiveId(null); setAttachments([]); setMedia([]); setArtifacts([]); }
  }, [user?.id, refreshConversations]); // eslint-disable-line react-hooks/exhaustive-deps

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    setActiveId(null);
    setMessages([]);
    setAttachments([]);
    setMedia([]);
    setArtifacts([]);
    setError(null);
    setStreaming(false);
  }, []);

  const openConversation = useCallback(async (id) => {
    abortRef.current?.abort();
    setActiveId(id);
    setAttachments([]);
    setError(null);
    setStreaming(false);
    try {
      const msgs = await api.getMessages(id);
      setMessages(msgs);
      refreshMedia(id);
      refreshArtifacts(id);
    } catch (e) {
      setMessages([]);
      setMedia([]);
      setArtifacts([]);
      setError(e.message);
    }
  }, [refreshMedia, refreshArtifacts]);

  const deleteConversation = useCallback(async (id) => {
    await api.deleteConversation(id);
    setConversations((c) => c.filter((x) => x.id !== id));
    if (activeRef.current === id) newChat();
  }, [newChat]);

  const addFiles = useCallback((files) => {
    Array.from(files).forEach(async (file) => {
      const isImage = file.type.startsWith('image/');
      const tmp = { tmpId: nextId('f'), kind: isImage ? 'image' : 'document', name: file.name, status: 'uploading' };
      setAttachments((a) => [...a, tmp]);
      try {
        const res = await (isImage ? api.uploadImage : api.uploadDocument)(file, activeRef.current);
        setAttachments((a) => a.map((x) => (x.tmpId === tmp.tmpId ? { ...x, ...res, status: 'ready' } : x)));
      } catch (e) {
        setAttachments((a) => a.map((x) => (x.tmpId === tmp.tmpId ? { ...x, status: 'error', error: e.message } : x)));
      }
    });
  }, []);

  const removeAttachment = useCallback((tmpId) => setAttachments((a) => a.filter((x) => x.tmpId !== tmpId)), []);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const attachmentsRef = useRef(attachments);
  attachmentsRef.current = attachments;

  const send = useCallback(async (text, { viaVoice = false } = {}) => {
    const ready = attachmentsRef.current.filter((a) => a.status === 'ready');
    const trimmed = text.trim();
    if (!trimmed && !ready.length) return null;

    const assistantId = nextId('a');
    setError(null);
    setAttachments([]);
    setMessages((m) => [
      ...m,
      {
        id: nextId('u'),
        role: 'user',
        content: trimmed,
        attachments: ready.map((a) => ({
          id: a.id,
          kind: a.kind,
          name: a.name,
          pages: a.pages,
          chars: a.chars,
          ocr_used: a.ocr_used,
          extracted_text: a.extracted_text,
          image_description: a.image_description,
        })),
      },
      { id: assistantId, role: 'assistant', content: '', pending: true },
    ]);
    setStreaming(true);

    const patch = (fields) =>
      setMessages((m) => m.map((x) => (x.id === assistantId ? { ...x, ...fields } : x)));

    let currentActivities = [];
    let currentSummary = '';
    let currentStatusText = '';
    let fullText = '';

    const updateActivity = (act) => {
      if (!act?.id) return;
      const idx = currentActivities.findIndex((x) => x.id === act.id);
      if (idx >= 0) {
        currentActivities = [
          ...currentActivities.slice(0, idx),
          { ...currentActivities[idx], ...act },
          ...currentActivities.slice(idx + 1),
        ];
      } else {
        currentActivities = [...currentActivities, act];
      }
      patch({ activities: [...currentActivities] });
    };

    const controller = new AbortController();
    abortRef.current = controller;
    let final = null;

    try {
      await streamChat(
        {
          conversation_id: activeRef.current,
          message: trimmed,
          attachment_ids: ready.map((a) => a.id),
          via_voice: viaVoice,
        },
        {
          meta: ({ conversation_id, title }) => {
            if (!activeRef.current) {
              activeRef.current = conversation_id;
              setActiveId(conversation_id);
            }
            if (title) {
              setConversations((prev) => {
                const exists = prev.some((c) => c.id === conversation_id);
                if (exists) {
                  return prev.map((c) => (c.id === conversation_id ? { ...c, title } : c));
                }
                return [{ id: conversation_id, title, updated_at: new Date().toISOString() }, ...prev];
              });
            }
          },
          title: ({ title: newTitle, conversation_id: cid }) => {
            const targetId = cid || activeRef.current;
            if (newTitle && targetId) {
              setConversations((prev) => {
                const exists = prev.some((c) => c.id === targetId);
                if (exists) {
                  return prev.map((c) => (c.id === targetId ? { ...c, title: newTitle } : c));
                }
                return [{ id: targetId, title: newTitle, updated_at: new Date().toISOString() }, ...prev];
              });
            }
          },
          status_update: ({ message }) => {
            currentStatusText = message || '';
            patch({ status_text: currentStatusText });
          },
          tool_started: (data) => {
            if (data?.id) {
              updateActivity(data);
              currentStatusText = data.label || currentStatusText;
              patch({ status_text: currentStatusText });
            }
          },
          tool_completed: (data) => {
            if (data?.id) updateActivity(data);
          },
          tool_failed: (data) => {
            if (data?.id) updateActivity({ ...data, status: 'failed' });
          },
          activity: (data) => {
            if (data?.id) updateActivity(data);
          },
          token: ({ text: t }) => {
            // Direct immediate rendering — no pacer, no timer, true streaming
            fullText += t;
            patch({ content: fullText });
          },
          sources: (sources) => patch({ sources }),
          sources_available: (sources) => patch({ sources }),
          follow_ups: ({ suggestions }) => {
            patch({ follow_ups: suggestions || [] });
          },
          artifact: (artifact) => {
            patch({ artifact });
            if (artifact) {
              setArtifacts((prev) => {
                const filtered = prev.filter((x) => x.id !== artifact.id);
                return [artifact, ...filtered];
              });
            }
          },
          task_completed: ({ activities, activity_summary, follow_ups: fu }) => {
            if (activities) currentActivities = activities;
            if (activity_summary) currentSummary = activity_summary;
            currentStatusText = '';
            patch({
              activities: currentActivities,
              activity_summary: currentSummary,
              status_text: '',
              ...(fu ? { follow_ups: fu } : {}),
            });
          },
          done: (info) => { final = info; },
          error: ({ message }) => { throw new Error(message); },
          task_error: ({ error: err, message }) => { throw new Error(err || message || 'Task failed'); },
        },
        controller.signal,
      );

      patch({
        content: fullText,
        pending: false,
        latency_ms: final?.latency_ms,
        model: final?.model,
        activities: currentActivities,
        activity_summary: currentSummary,
        status_text: '',
      });
      refreshConversations();
      refreshMedia(activeRef.current);
      refreshArtifacts(activeRef.current);
      return { id: assistantId, content: fullText };
    } catch (e) {
      if (e.name === 'AbortError') {
        patch({ content: fullText || 'Stopped.', pending: false, status_text: '' });
      } else {
        setError(e.message);
        patch({ content: fullText, pending: false, failed: true, status_text: '' });
      }
      return null;
    } finally {
      setStreaming(false);
    }
  }, [refreshConversations, refreshMedia, refreshArtifacts]);

  const state = useMemo(
    () => ({ conversations, activeId, messages, attachments, media, artifacts, streaming, error }),
    [conversations, activeId, messages, attachments, media, artifacts, streaming, error],
  );
  const actions = useMemo(
    () => ({ newChat, openConversation, deleteConversation, addFiles, removeAttachment, send, stop, refreshConversations, refreshMedia, refreshArtifacts }),
    [newChat, openConversation, deleteConversation, addFiles, removeAttachment, send, stop, refreshConversations, refreshMedia, refreshArtifacts],
  );

  return (
    <ChatActionsCtx.Provider value={actions}>
      <ChatStateCtx.Provider value={state}>{children}</ChatStateCtx.Provider>
    </ChatActionsCtx.Provider>
  );
}

export const useChatState = () => useContext(ChatStateCtx);
export const useChatActions = () => useContext(ChatActionsCtx);
