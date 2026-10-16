import { memo } from 'react';
import { Loader2 } from 'lucide-react';

/**
 * AgentStatus
 * Displays short, muted task-status text above or between assistant responses.
 * When running, displays an animated micro-pulse indicator.
 */
function AgentStatus({ text, isRunning = false }) {
  if (!text) return null;

  return (
    <div
      className={`agent-task-status ${isRunning ? 'running' : 'completed'}`}
      role="status"
      aria-live="polite"
    >
      {isRunning ? (
        <span className="status-indicator">
          <Loader2 size={13} className="spin text-accent" aria-hidden />
        </span>
      ) : (
        <span className="status-dot-done" aria-hidden />
      )}
      <span className="status-text">{text}</span>
    </div>
  );
}

export default memo(AgentStatus);
