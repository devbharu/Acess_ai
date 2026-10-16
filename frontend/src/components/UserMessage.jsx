import { memo } from 'react';
import { FileText, Image as ImageIcon } from 'lucide-react';

/**
 * UserMessage
 * User message bubble aligned to the right with AccessAI orange styling and attachment chips.
 */
function UserMessage({ content, attachments = [], onSelectAttachment }) {
  return (
    <div className="chat-row user-row">
      {!!attachments?.length && (
        <div className="user-attach-grid">
          {attachments.map((a, i) => (
            <button
              key={a.id || i}
              type="button"
              className="chip chip-interactive"
              onClick={() => onSelectAttachment && onSelectAttachment(a)}
              title={`Inspect ${a.name}`}
            >
              {a.kind === 'image' && a.id ? (
                <img
                  src={`/api/attachments/${a.id}/file`}
                  alt=""
                  className="chip-thumb"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              ) : a.kind === 'image' ? (
                <ImageIcon size={14} />
              ) : (
                <FileText size={14} />
              )}
              <span className="name">{a.name}</span>
            </button>
          ))}
        </div>
      )}
      <div className="user-pill">{content}</div>
    </div>
  );
}

export default memo(UserMessage);
