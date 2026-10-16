import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, Camera, FileText, Image as ImageIcon, Loader2, Mic, Paperclip, Square, X } from 'lucide-react';
import { api } from '../api/client';
import { speechStore } from '../audio/speech';
import { MODELS } from '../config/models';
import { useChatActions, useChatState } from '../context/ChatContext';
import { useSettings } from '../context/SettingsContext';
import { useRecorder } from '../hooks/useRecorder';

const Chips = memo(function Chips({ items, onRemove }) {
  if (!items.length) return null;
  return (
    <div className="composer-chips">
      {items.map((a) => (
        <span key={a.tmpId} className={`chip ${a.status === 'error' ? 'error' : ''}`} title={a.error}>
          {a.status === 'uploading' ? <Loader2 size={15} className="spin" /> : a.kind === 'image' ? <ImageIcon size={15} /> : <FileText size={15} />}
          <span className="name">{a.name}</span>
          <button type="button" className="icon-btn sm" style={{ width: 26, height: 26 }} onClick={() => onRemove(a.tmpId)} aria-label={`Remove ${a.name}`}><X size={14} /></button>
        </span>
      ))}
    </div>
  );
});

export default function Composer() {
  const { attachments, streaming } = useChatState();
  const { addFiles, removeAttachment, send, stop } = useChatActions();
  const { settings, update } = useSettings();
  const rec = useRecorder();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false); // transcribing
  const [voiceError, setVoiceError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const area = useRef(null);
  const fileInput = useRef(null);
  const camInput = useRef(null);

  useEffect(() => {
    const el = area.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  const submit = useCallback(async (value, viaVoice = false) => {
    setText('');
    speechStore.stop();
    const reply = await send(value, { viaVoice });
    const mode = settings.auto_speak;
    if (reply && (mode === 'always' || (mode === 'voice' && viaVoice))) {
      speechStore.speak(reply.id, reply.content, { voice: settings.tts_voice, speed: settings.tts_speed });
    }
  }, [send, settings.auto_speak, settings.tts_voice, settings.tts_speed]);

  const toggleMic = useCallback(async () => {
    setVoiceError(null);
    if (!rec.recording) { speechStore.stop(); await rec.start(); return; }
    const blob = await rec.stop();
    if (!blob || blob.size < 800) return;
    setBusy(true);
    try {
      const { text: heard } = await api.stt(blob, { language: settings.stt_language, model: settings.stt_model });
      if (!heard?.trim()) setVoiceError('I could not hear anything. Please try again.');
      else if (settings.auto_send) await submit(heard, true);
      else setText((t) => (t ? `${t} ${heard}` : heard));
    } catch (e) {
      setVoiceError(e.message);
    } finally {
      setBusy(false);
    }
  }, [rec, settings.stt_language, settings.stt_model, settings.auto_send, submit]);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (!streaming) submit(text);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  const uploading = attachments.some((a) => a.status === 'uploading');
  const canSend = !uploading && (text.trim() || attachments.some((a) => a.status === 'ready'));

  return (
    <div
      className={`composer ${dragging ? 'dragging' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <Chips items={attachments} onRemove={removeAttachment} />
      <label htmlFor="composer-input" className="sr-only">Message AccessAI</label>
      <textarea
        id="composer-input" ref={area} rows={1} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKeyDown}
        placeholder={rec.recording ? 'Listening…' : 'Ask about a document or image, or press the microphone'}
      />
      <div className="composer-bar">
        <input ref={fileInput} type="file" multiple hidden onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
        <input ref={camInput} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
        <button type="button" className="icon-btn" onClick={() => fileInput.current.click()} aria-label="Attach documents or images" title="Attach files"><Paperclip size={20} /></button>
        <button type="button" className="icon-btn" onClick={() => camInput.current.click()} aria-label="Take a photo" title="Take a photo"><Camera size={20} /></button>

        <div className="composer-model-wrap">
          <label htmlFor="model-select" className="sr-only">Model</label>
          <select
            id="model-select"
            className="composer-model-select"
            value={settings.model}
            onChange={(e) => update({ model: e.target.value })}
            title="Switch AI model"
            aria-label="Model"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}{m.multimodal ? ' (Vision)' : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="grow" aria-live="polite">
          {rec.recording && <span className="rec-pill"><i className="rec-dot" /> Recording {String(Math.floor(rec.seconds / 60)).padStart(2, '0')}:{String(rec.seconds % 60).padStart(2, '0')}</span>}
          {busy && <span className="rec-pill"><Loader2 size={15} className="spin" /> Transcribing…</span>}
          {(voiceError || rec.error) && <span className="error-text">{voiceError || rec.error}</span>}
        </div>
        <button type="button" className={`icon-btn ${rec.recording ? 'on' : ''}`} onClick={toggleMic} disabled={busy || streaming}
          aria-label={rec.recording ? 'Stop recording and send' : 'Ask by voice'} title={rec.recording ? 'Stop recording' : 'Ask by voice'}>
          {rec.recording ? <Square size={18} fill="currentColor" /> : <Mic size={20} />}
        </button>
        {streaming ? (
          <button type="button" className="send-btn" onClick={stop} aria-label="Stop generating"><Square size={16} fill="currentColor" /></button>
        ) : (
          <button type="button" className="send-btn" onClick={() => submit(text)} disabled={!canSend} aria-label="Send message"><ArrowUp size={22} /></button>
        )}
      </div>
    </div>
  );
}
