import { memo } from 'react';
import { ChevronRight, Eye } from 'lucide-react';

/**
 * SourceCitations
 * Renders verified evidence passages, source documents, and page references.
 */
function SourceCitations({ sources = [], onSelectAttachment }) {
  const meaningfulSources = (sources || []).filter(
    (s) => s.type !== 'tool' && (Boolean(s.text?.trim()) || s.page != null || Boolean(s.evidence?.trim()))
  );

  if (!meaningfulSources.length) return null;

  return (
    <details className="evidence">
      <summary>
        <ChevronRight size={16} className="chev" aria-hidden /> Evidence used ({meaningfulSources.length})
      </summary>
      <div className="evidence-list">
        {meaningfulSources.map((s, i) => (
          <div className="evidence-item" key={i}>
            <header>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="tag">{s.type || 'document'}</span>
                <span>
                  {s.source || s.filename}
                  {s.page ? ` · page ${s.page}` : ''}
                  {s.section ? ` · ${s.section}` : ''}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {s.score != null && <span className="msg-meta">{(s.score * 100).toFixed(0)}% match</span>}
                {onSelectAttachment && (s.source || s.filename) && (
                  <button
                    type="button"
                    className="evidence-inspect-btn"
                    onClick={() =>
                      onSelectAttachment({
                        name: s.source || s.filename,
                        kind: s.type === 'image' || s.type === 'ocr' ? 'image' : 'document',
                      })
                    }
                    title={`Inspect ${s.source || s.filename}`}
                    aria-label={`Inspect ${s.source || s.filename}`}
                  >
                    <Eye size={12} /> Inspect
                  </button>
                )}
              </div>
            </header>
            <p>{s.text || s.evidence}</p>
          </div>
        ))}
      </div>
    </details>
  );
}

export default memo(SourceCitations);
