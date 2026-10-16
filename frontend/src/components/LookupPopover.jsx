import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

/**
 * LookupPopover
 * Reusable macOS Look Up dictionary-style popover card.
 * Dedicated purely to seeing the contents cleanly (no extra clutter).
 *
 * Used for both Media and Artifacts separately.
 */
export default function LookupPopover({
  title,
  items = [],
  emptyMessage = 'No items in this conversation.',
  onClose,
  alignRight = false,
}) {
  const popoverRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        onClose?.();
      }
    }
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose?.();
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      ref={popoverRef}
      className={`mac-lookup-popover ${alignRight ? 'align-right' : ''}`}
      role="dialog"
      aria-label={`${title} contents`}
    >
      {/* Upward pointing Caret */}
      <div className="mac-lookup-caret" aria-hidden="true" />

      {/* Header: Title + Hairline Rule + Count Badge + Close */}
      <div className="mac-lookup-header">
        <div className="mac-lookup-title-row">
          <span className="mac-lookup-category">{title}</span>
          <div className="mac-lookup-rule" />
          <span className="mac-lookup-badge">{items.length}</span>
          <button
            type="button"
            className="mac-lookup-close-btn"
            onClick={onClose}
            aria-label={`Close ${title}`}
            title="Close"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Body: Pure contents view */}
      <div className="mac-lookup-body">
        {items.length === 0 ? (
          <div className="mac-lookup-empty-text">{emptyMessage}</div>
        ) : (
          <div className="mac-lookup-entries">
            {items.map((item, idx) => (
              <article key={item.id || idx} className="mac-lookup-entry">
                {/* Word / Title + Phonetic / Meta */}
                <div className="mac-lookup-entry-head">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mac-lookup-word mac-lookup-link"
                      title={`Open ${item.name}`}
                    >
                      {item.name}
                    </a>
                  ) : (
                    <span className="mac-lookup-word">{item.name}</span>
                  )}
                  {item.meta && (
                    <span className="mac-lookup-phonetic">{item.meta}</span>
                  )}
                </div>

                {/* Definition / Content excerpt */}
                {item.content && (
                  <div className="mac-lookup-definition">
                    <span className="mac-lookup-def-num">{idx + 1}</span>
                    <p className="mac-lookup-def-text">{item.content}</p>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
