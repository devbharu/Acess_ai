import { lazy, memo, Suspense, useCallback, useState } from 'react';
import { Check, Copy, Sparkles } from 'lucide-react';
import AgentActivityTimeline from './AgentActivityTimeline';
import ReportDownload from './ReportDownload';
import AudioPlayer from './AudioPlayer';
import { modelLabel } from '../config/models';

const Markdown = lazy(() => import('./Markdown'));

function CopyButton({ text }) {
  const [done, setDone] = useState(false);
  const copy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    setDone(true);
    setTimeout(() => setDone(false), 1500);
  }, [text]);

  return (
    <button
      type="button"
      className="chat-action-btn"
      onClick={copy}
      aria-label={done ? 'Copied' : 'Copy answer'}
      title="Copy"
    >
      {done ? <Check size={16} /> : <Copy size={16} />}
    </button>
  );
}

/**
 * FollowUpSuggestions
 * Renders contextual follow-up question chips after the assistant response.
 */
function FollowUpSuggestions({ suggestions, onSend }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="follow-up-container">
      {suggestions.map((s, i) => (
        <button
          key={i}
          type="button"
          className="follow-up-chip"
          onClick={() => onSend && onSend(s)}
        >
          <Sparkles size={13} className="follow-up-icon" />
          <span>{s}</span>
        </button>
      ))}
    </div>
  );
}

/**
 * ProgressIndicator
 * Claude-style single progress indicator with rotating status labels.
 * Shows only one clean animated state instead of double loaders.
 */
function ProgressIndicator({ statusText }) {
  const label = statusText || 'Thinking';

  return (
    <div className="progress-indicator" role="status" aria-label="AccessAI is working">
      <div className="progress-dots">
        <span className="progress-dot" />
        <span className="progress-dot" />
        <span className="progress-dot" />
      </div>
      <span className="progress-label">{label}</span>
    </div>
  );
}

/**
 * AssistantMessage
 * Left-aligned assistant turn with:
 * - Claude-style single progress indicator (no double loader)
 * - Expandable/collapsible activity summary
 * - Conversational content with Markdown
 * - Follow-up suggestion chips at the end
 * - No "Evidence used" section
 * - Persistent action buttons
 */
function AssistantMessage({ message, onSelectAttachment, onSendSuggestion }) {
  const {
    id,
    content,
    artifact,
    activities = [],
    activity_summary = '',
    status_text = '',
    follow_ups = [],
    pending = false,
    failed = false,
    latency_ms: latency,
    model,
  } = message;

  const hasActivities = activities && activities.length > 0;
  const isRunning = pending;
  const showProgress = isRunning && !content;

  return (
    <div className="chat-row assistant-row">
      <div className="assistant-content">
        {/* 1. Claude-style single progress indicator — replaces both AgentStatus + typing dots */}
        {showProgress && (
          <ProgressIndicator statusText={status_text} />
        )}

        {/* 2. Claude-style Expandable & Collapsible Activity Timeline */}
        {hasActivities && (
          <AgentActivityTimeline
            activities={activities}
            summary={activity_summary}
            isRunning={isRunning}
          />
        )}

        {/* 3. Assistant Conversational Content */}
        {content ? (
          <div className="assistant-text" aria-live={pending ? 'polite' : 'off'}>
            <Suspense fallback={<p style={{ whiteSpace: 'pre-wrap' }}>{content}</p>}>
              <Markdown>{content}</Markdown>
            </Suspense>
            {failed && <p className="error-text">The response was interrupted.</p>}
          </div>
        ) : null}

        {/* 4. AI Generated PDF Report Download */}
        {artifact && <ReportDownload artifact={artifact} />}

        {/* 5. Follow-up suggestion chips */}
        {!pending && follow_ups && follow_ups.length > 0 && (
          <FollowUpSuggestions
            suggestions={follow_ups}
            onSend={onSendSuggestion}
          />
        )}

        {/* 6. Action icons row (Copy, Read aloud, Latency) */}
        {!pending && content && (
          <div className="assistant-actions">
            <CopyButton text={content} />
            <AudioPlayer id={id} text={content} />
            {latency != null && (
              <span className="assistant-meta">
                {(latency / 1000).toFixed(1)}s{model ? ` · ${modelLabel(model)}` : ''}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(AssistantMessage);
