import { memo, useState } from 'react';
import {
  Check,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Loader2,
  FileText,
  Search,
  Sparkles,
  Eye,
  Scan,
  Download,
} from 'lucide-react';

function getToolIcon(type) {
  switch (type) {
    case 'outline':
    case 'read':
    case 'read_page':
      return <FileText size={13} />;
    case 'search':
      return <Search size={13} />;
    case 'ocr':
      return <Scan size={13} />;
    case 'inspect_image':
    case 'vision':
    case 'diagram':
      return <Eye size={13} />;
    case 'report':
    case 'generate_report':
      return <Download size={13} />;
    default:
      return <Sparkles size={13} />;
  }
}

/**
 * ActivityStep
 * An individual row in Claude's activity timeline describing genuine backend work.
 */
function ActivityStep({ activity }) {
  const [expanded, setExpanded] = useState(false);

  const {
    label,
    type,
    status = 'completed',
    detail,
    duration_ms,
    metadata = {},
    error,
  } = activity;

  const isRunning = status === 'running';
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed';

  const hasDrawer = Boolean(detail || error || Object.keys(metadata).length > 0);
  const targetFile = metadata?.file || metadata?.doc || metadata?.filename;
  const targetPage = metadata?.page;

  const formatDuration = (ms) => {
    if (!ms) return null;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className={`activity-step ${status} ${hasDrawer ? 'interactive' : ''}`}>
      <div
        className="activity-step-row"
        onClick={() => hasDrawer && setExpanded((e) => !e)}
        role={hasDrawer ? 'button' : undefined}
        tabIndex={hasDrawer ? 0 : undefined}
        onKeyDown={(e) => {
          if (hasDrawer && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            setExpanded((s) => !s);
          }
        }}
        aria-expanded={hasDrawer ? expanded : undefined}
      >
        <div className="activity-status-icon" aria-hidden>
          {isRunning ? (
            <Loader2 size={13} className="spin text-accent" />
          ) : isFailed ? (
            <AlertCircle size={13} className="text-error" />
          ) : (
            <Check size={13} className="text-success" />
          )}
        </div>

        <div className="activity-type-icon" aria-hidden>
          {getToolIcon(type)}
        </div>

        <div className="activity-label-wrap">
          <span className="activity-label">{label}</span>
          {targetFile && (
            <span className="activity-file-badge">
              {targetFile}
              {targetPage ? ` : p.${targetPage}` : ''}
            </span>
          )}
        </div>

        <div className="activity-meta-wrap">
          {duration_ms != null && (
            <span className="activity-duration">{formatDuration(duration_ms)}</span>
          )}
          {hasDrawer && (
            <span className="activity-chevron" aria-hidden>
              {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          )}
        </div>
      </div>

      {hasDrawer && expanded && (
        <div className="activity-drawer" role="region" aria-label={`Details for ${label}`}>
          {detail && <div className="activity-detail-text">{detail}</div>}
          {error && <div className="activity-error-text"><strong>Error:</strong> {error}</div>}
          {metadata && Object.keys(metadata).length > 0 && (
            <div className="activity-params">
              {Object.entries(metadata).map(([k, v]) => (
                <span key={k} className="activity-param-pill">
                  <span className="param-k">{k}:</span> <span className="param-v">{String(v)}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(ActivityStep);
