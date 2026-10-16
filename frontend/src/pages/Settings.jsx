import { memo, useState } from 'react';
import { Brush, Check, Cpu, Library, Loader2, Mic2, RotateCcw, ScrollText, User } from 'lucide-react';
import { Field, Segmented, Slider, Toggle } from '../components/Controls';
import { DEFAULT_SETTINGS, DEFAULT_SYSTEM_PROMPT, MODELS, PARAMS, RETRIEVAL_PARAMS, STT_LANGUAGES, STT_MODELS, TTS_VOICES } from '../config/models';
import { useAuth } from '../context/AuthContext';
import { useSettings } from '../context/SettingsContext';
import { useTheme } from '../context/ThemeContext';

const TABS = [
  ['model', 'Model', Cpu],
  ['prompt', 'System prompt', ScrollText],
  ['retrieval', 'Retrieval', Library],
  ['voice', 'Voice', Mic2],
  ['profile', 'Profile', User],
  ['appearance', 'Appearance', Brush],
];

const PRESETS = {
  Strict: DEFAULT_SYSTEM_PROMPT,
  Detailed: `${DEFAULT_SYSTEM_PROMPT}\nWhen describing images, mention objects, text, colours, people and layout in a logical order.`,
  'Plain & short': `You are AccessAI. Answer from the supplied evidence only, in at most three short sentences. If it is not in the evidence, say so.`,
};

const fmt = (key, v) => (key === 'num_ctx' || key === 'num_predict' ? v.toLocaleString() : v);

const ModelPanel = memo(function ModelPanel({ settings, update }) {
  return (
    <div className="panel">
      <div className="model-grid" role="radiogroup" aria-label="Model">
        {MODELS.map((m) => (
          <button key={m.id} type="button" role="radio" className="model-card" aria-checked={settings.model === m.id} onClick={() => update({ model: m.id })}>
            <div className="row">
              <span className="tag">{m.family}</span>
              {m.multimodal && <span className="tag vision-tag">Vision</span>}
              {settings.model === m.id && <Check size={18} aria-hidden />}
            </div>
            <strong>{m.label}</strong>
            <code>{m.id}</code>
          </button>
        ))}
      </div>
      <hr className="divider" />
      <div className="grid-2">
        {PARAMS.map(({ key, ...rest }) => (
          <Slider key={key} {...rest} value={settings[key]} onChange={(v) => update({ [key]: v })} format={(v) => fmt(key, v)} />
        ))}
        <Field label="Seed" hint="Leave empty for a different answer each time. Set a number to make answers repeatable.">
          {(id) => (
            <input id={id} type="number" className="input" placeholder="Random" value={settings.seed ?? ''}
              onChange={(e) => update({ seed: e.target.value === '' ? null : Number(e.target.value) })} />
          )}
        </Field>
      </div>
    </div>
  );
});

const PromptPanel = memo(function PromptPanel({ settings, update }) {
  return (
    <div className="panel">
      <div className="presets" role="group" aria-label="Prompt presets">
        {Object.entries(PRESETS).map(([name, text]) => (
          <button key={name} type="button" className="btn btn-sm" onClick={() => update({ system_prompt: text })}>{name}</button>
        ))}
        <button type="button" className="btn btn-sm" onClick={() => update({ system_prompt: DEFAULT_SYSTEM_PROMPT })}><RotateCcw size={14} /> Reset</button>
      </div>
      <Field label="System prompt" hint="Sent to the model before every question. Keep the rule about answering only from evidence to limit hallucination.">
        {(id) => <textarea id={id} className="textarea" rows={12} value={settings.system_prompt} onChange={(e) => update({ system_prompt: e.target.value })} />}
      </Field>
      <Toggle label="Strict grounding" hint="Refuse to answer when no supporting passage is found."
        checked={settings.grounded_only} onChange={(v) => update({ grounded_only: v })} />
    </div>
  );
});

const RetrievalPanel = memo(function RetrievalPanel({ settings, update }) {
  return (
    <div className="panel">
      <p className="hint">Documents are split into overlapping chunks, embedded and stored in FAISS. These values apply to files uploaded after the change.</p>
      <div className="grid-2">
        {RETRIEVAL_PARAMS.map(({ key, ...rest }) => <Slider key={key} {...rest} value={settings[key]} onChange={(v) => update({ [key]: v })} />)}
      </div>
    </div>
  );
});

const VoicePanel = memo(function VoicePanel({ settings, update }) {
  return (
    <div className="panel">
      <div className="grid-2">
        <Field label="Speech recognition model" hint="Larger models are more accurate but slower.">
          {(id) => <select id={id} className="select" value={settings.stt_model} onChange={(e) => update({ stt_model: e.target.value })}>
            {STT_MODELS.map((m) => <option key={m} value={m}>Whisper {m}</option>)}</select>}
        </Field>
        <Field label="Spoken language">
          {(id) => <select id={id} className="select" value={settings.stt_language} onChange={(e) => update({ stt_language: e.target.value })}>
            {STT_LANGUAGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>}
        </Field>
        <Field label="Voice for answers">
          {(id) => <select id={id} className="select" value={settings.tts_voice} onChange={(e) => update({ tts_voice: e.target.value })}>
            {TTS_VOICES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>}
        </Field>
        <Slider label="Speaking speed" min={0.6} max={1.6} step={0.05} value={settings.tts_speed} onChange={(v) => update({ tts_speed: v })} format={(v) => `${v.toFixed(2)}×`} />
      </div>
      <hr className="divider" />
      <div>
        <span className="label">Read answers aloud</span>
        <div style={{ marginTop: 8 }}>
          <Segmented label="Read answers aloud" value={settings.auto_speak} onChange={(v) => update({ auto_speak: v })}
            options={[['voice', 'After voice questions'], ['always', 'Always'], ['off', 'Never']]} />
        </div>
      </div>
      <Toggle label="Send voice questions automatically" hint="Off: the transcript is placed in the box so you can edit it first."
        checked={settings.auto_send} onChange={(v) => update({ auto_send: v })} />
    </div>
  );
});

function ProfilePanel() {
  const { user, updateProfile, logout } = useAuth();
  const [form, setForm] = useState({ name: user?.name || '', email: user?.email || '', password: '' });
  const [state, setState] = useState({ busy: false, msg: '', err: '' });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async (e) => {
    e.preventDefault();
    setState({ busy: true, msg: '', err: '' });
    try {
      const patch = { name: form.name, email: form.email };
      if (form.password) patch.password = form.password;
      await updateProfile(patch);
      setForm((f) => ({ ...f, password: '' }));
      setState({ busy: false, msg: 'Profile saved.', err: '' });
    } catch (err) {
      setState({ busy: false, msg: '', err: err.message });
    }
  };

  return (
    <form className="panel" onSubmit={save} style={{ maxWidth: 520 }}>
      <Field label="Name">{(id) => <input id={id} className="input" required value={form.name} onChange={set('name')} />}</Field>
      <Field label="Email">{(id) => <input id={id} type="email" className="input" required value={form.email} onChange={set('email')} />}</Field>
      <Field label="New password" hint="Leave empty to keep your current password.">
        {(id) => <input id={id} type="password" className="input" minLength={8} autoComplete="new-password" value={form.password} onChange={set('password')} />}
      </Field>
      <p role="status" className={state.err ? 'error-text' : 'hint'}>{state.err || state.msg}</p>
      <div style={{ display: 'flex', gap: 10 }}>
        <button type="submit" className="btn btn-primary" disabled={state.busy}>{state.busy && <Loader2 size={16} className="spin" />} Save changes</button>
        <button type="button" className="btn btn-danger" onClick={logout}>Sign out</button>
      </div>
    </form>
  );
}

function AppearancePanel() {
  const { theme, setTheme, fontScale, setFontScale, reduceMotion, setReduceMotion } = useTheme();
  return (
    <div className="panel" style={{ maxWidth: 560 }}>
      <div>
        <span className="label">Theme</span>
        <div style={{ marginTop: 8 }}>
          <Segmented label="Theme" value={theme} onChange={setTheme}
            options={[['system', 'System'], ['light', 'Light'], ['dark', 'Dark'], ['contrast', 'High contrast']]} />
        </div>
      </div>
      <Slider label="Text size" min={0.9} max={1.5} step={0.05} value={fontScale} onChange={setFontScale} format={(v) => `${Math.round(v * 100)}%`} hint="Scales the whole interface." />
      <Toggle label="Reduce motion" hint="Turns off animations and transitions." checked={reduceMotion} onChange={setReduceMotion} />
    </div>
  );
}

export default function Settings() {
  const [tab, setTab] = useState('model');
  const { settings, update, reset, status } = useSettings();
  const onKey = (e) => {
    const i = TABS.findIndex(([k]) => k === tab);
    if (e.key === 'ArrowRight') setTab(TABS[(i + 1) % TABS.length][0]);
    if (e.key === 'ArrowLeft') setTab(TABS[(i - 1 + TABS.length) % TABS.length][0]);
  };

  return (
    <div className="page">
      <div className="page-inner">
        <div className="page-head">
          <div>
            <h1>Settings</h1>
            <p>Control the model, how it is instructed and how you talk to it. Changes save automatically.</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span className="save-state" role="status">
              {status === 'saving' && <><Loader2 size={15} className="spin" /> Saving…</>}
              {status === 'saved' && <><Check size={15} /> Saved</>}
              {status === 'error' && <span className="error-text">Could not save</span>}
            </span>
            <button type="button" className="btn btn-sm" onClick={reset}><RotateCcw size={14} /> Reset defaults</button>
          </div>
        </div>

        <div className="tabs" role="tablist" aria-label="Settings sections" onKeyDown={onKey}>
          {TABS.map(([key, label, Icon]) => (
            <button key={key} type="button" role="tab" id={`tab-${key}`} aria-selected={tab === key} aria-controls={`panel-${key}`}
              tabIndex={tab === key ? 0 : -1} onClick={() => setTab(key)}><Icon size={18} /> {label}</button>
          ))}
        </div>

        <section role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {tab === 'model' && <ModelPanel settings={settings} update={update} />}
          {tab === 'prompt' && <PromptPanel settings={settings} update={update} />}
          {tab === 'retrieval' && <RetrievalPanel settings={settings} update={update} />}
          {tab === 'voice' && <VoicePanel settings={settings} update={update} />}
          {tab === 'profile' && <ProfilePanel />}
          {tab === 'appearance' && <AppearancePanel />}
        </section>
      </div>
    </div>
  );
}
