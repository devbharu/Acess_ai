import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Copy, Check, FileText, Image as ImageIcon, Paperclip, Volume2, X } from 'lucide-react';
import Composer from '../components/Composer';
import ConversationHeader from '../components/ConversationHeader';
import MessageList from '../components/MessageList';
import { MODELS, SUGGESTIONS, AGENT_SUGGESTIONS } from '../config/models';
import { useChatActions, useChatState } from '../context/ChatContext';
import { useSettings } from '../context/SettingsContext';
import { speechStore } from '../audio/speech';

function MediaModal({ item, onClose, settings }) {
  const [copied, setCopied] = useState(false);
  const isImage = item.kind === 'image';

  const copyText = (t) => {
    navigator.clipboard.writeText(t);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const speak = (t) => {
    speechStore.speak(`modal-${item.id}`, t, {
      voice: settings.tts_voice,
      speed: settings.tts_speed,
    });
  };

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <h2 id="modal-title">
            {isImage ? <ImageIcon size={20} /> : <FileText size={20} />}
            <span>{item.name}</span>
            <span className="tag">{isImage ? 'Image' : 'Document'}</span>
          </h2>
          <button type="button" className="icon-btn sm" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </header>

        <div className="modal-body">
          {isImage && (
            <img
              src={`/api/attachments/${item.id}/file`}
              alt={item.name}
              className="modal-img-preview"
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
          )}

          {isImage && item.image_description && (
            <section className="meta-section">
              <header>
                <span>AI Scene Understanding</span>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => speak(item.image_description)}
                >
                  <Volume2 size={14} /> Read aloud
                </button>
              </header>
              <p>{item.image_description}</p>
            </section>
          )}

          {item.extracted_text && (
            <section className="meta-section">
              <header>
                <span>{item.ocr_used ? 'OCR Extracted Text' : 'Document Content'}</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => speak(item.extracted_text)}
                  >
                    <Volume2 size={14} /> Read aloud
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => copyText(item.extracted_text)}
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />} Copy
                  </button>
                </div>
              </header>
              <p style={{ maxHeight: 200, overflowY: 'auto' }}>{item.extracted_text}</p>
            </section>
          )}

          {!isImage && (
            <div style={{ display: 'flex', gap: 16, fontSize: '0.85rem', color: 'var(--muted)', flexWrap: 'wrap' }}>
              {item.pages != null && <span>Pages: <strong>{item.pages}</strong></span>}
              {item.chars != null && <span>Characters: <strong>{item.chars?.toLocaleString()}</strong></span>}
              {item.ocr_used ? <span className="tag">OCR Processed</span> : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Chat() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { messages, activeId, conversations, media = [], artifacts = [], error } = useChatState();
  const { openConversation, newChat, addFiles, send } = useChatActions();
  const { settings, update } = useSettings();
  const scroller = useRef(null);
  const stick = useRef(true);
  const [announce, setAnnounce] = useState('');
  const [selectedMedia, setSelectedMedia] = useState(null);

  // Combine artifacts from state and any message-level artifacts
  const allArtifacts = useMemo(() => {
    const list = Array.isArray(artifacts) ? [...artifacts] : [];
    if (Array.isArray(messages)) {
      messages.forEach((m) => {
        if (m.artifact && !list.some((a) => a.id === m.artifact.id)) {
          list.unshift(m.artifact);
        }
      });
    }
    return list;
  }, [artifacts, messages]);

  // URL -> state
  useEffect(() => {
    if (id && id !== activeId) openConversation(id);
    if (!id && activeId) newChat();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // state -> URL (when a first message creates a conversation)
  useEffect(() => {
    if (activeId && !id) navigate(`/chat/${activeId}`, { replace: true });
  }, [activeId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll while the user is near the bottom.
  useEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const onScroll = useCallback(() => {
    const el = scroller.current;
    stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }, []);

  // Screen-reader announcement once an answer is complete.
  const last = messages[messages.length - 1];
  useEffect(() => {
    if (last?.role === 'assistant' && !last.pending && last.content) setAnnounce('Answer ready.');
    else setAnnounce('');
  }, [last?.id, last?.pending]); // eslint-disable-line react-hooks/exhaustive-deps

  const title = conversations.find((c) => c.id === activeId)?.title || 'New conversation';
  const onDropPage = (e) => { if (e.dataTransfer.files.length) { e.preventDefault(); addFiles(e.dataTransfer.files); } };

  return (
    <div className="chat" onDragOver={(e) => e.preventDefault()} onDrop={onDropPage}>
      <ConversationHeader
        title={title}
        media={media}
        artifacts={allArtifacts}
        mediaCount={media.length}
      />

      <div className="chat-scroll" ref={scroller} onScroll={onScroll}>
        <div className="chat-inner">
          <MessageList
            messages={messages}
            error={error}
            onSendSuggestion={(prompt) => send(prompt)}
            onSelectAttachment={(att) => {
              const found = media.find((x) => x.id === att.id || x.name === att.name) || att;
              setSelectedMedia(found);
            }}
          />
        </div>
      </div>

      <div className="chat-foot">
        <div className="chat-foot-inner">
          <Composer />
          <small>AccessAI answers from your files only. Check important details such as amounts and dates.</small>
        </div>
      </div>
      <div className="sr-only" role="status" aria-live="polite">{announce}</div>

      {selectedMedia && (
        <MediaModal item={selectedMedia} onClose={() => setSelectedMedia(null)} settings={settings} />
      )}
    </div>
  );
}
