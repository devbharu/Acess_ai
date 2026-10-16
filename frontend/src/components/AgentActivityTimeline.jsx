import { memo, useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import ActivityStep from './ActivityStep';

/**
 * AgentActivityTimeline
 * Expandable and collapsible activity summary similar to Claude's coding agent timeline.
 * Displays genuine backend operations executed during the request.
 */
function AgentActivityTimeline({ activities = [], summary = '', isRunning = false }) {
  // Start expanded while running or when there are 1-5 activities; allow user to toggle
  const [expanded, setExpanded] = useState(true);
  const containerRef = useRef(null);

  // Auto-scroll inside the activity drawer when new steps arrive while running
  useEffect(() => {
    if (isRunning && expanded && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [activities.length, isRunning, expanded]);

  if (!activities || activities.length === 0) return null;

  const count = activities.length;
  const runningCount = activities.filter((a) => a.status === 'running').length;
  const failedCount = activities.filter((a) => a.status === 'failed').length;

  // Fallback summary if not provided
  const displaySummary = summary || `Ran ${count} operation${count !== 1 ? 's' : ''}`;

  return (
    <div className={`agent-activity-timeline ${isRunning ? 'is-running' : ''}`}>
      <button
        type="button"
        className="activity-summary-toggle"
        onClick={() => setExpanded((s) => !s)}
        aria-expanded={expanded}
        aria-label={`${displaySummary}, click to ${expanded ? 'collapse' : 'expand'} activity details`}
      >
        <div className="activity-summary-left">
          <Terminal size={14} className="activity-terminal-icon" aria-hidden />
          <span className="activity-summary-text">{displaySummary}</span>
          {runningCount > 0 && (
            <span className="activity-pill-running">
              {runningCount} in progress
            </span>
          )}
          {failedCount > 0 && (
            <span className="activity-pill-failed">
              {failedCount} failed
            </span>
          )}
        </div>
        <div className="activity-summary-right" aria-hidden>
          {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </div>
      </button>

      {expanded && (
        <div
          className="activity-steps-container"
          ref={containerRef}
          role="region"
          aria-label="Agent execution steps"
        >
          {activities.map((act, index) => (
            <ActivityStep
              key={act.id || `act-${index}`}
              activity={act}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(AgentActivityTimeline);
