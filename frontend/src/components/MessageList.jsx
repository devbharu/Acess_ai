import { memo } from 'react';
import { FileText, Search, Image as ImageIcon, FileSpreadsheet } from 'lucide-react';
import Message from './Message';
import { AGENT_SUGGESTIONS } from '../config/models';

const ICON_MAP = {
  FileText,
  Search,
  Image: ImageIcon,
  FileSpreadsheet,
};

/**
 * MessageList
 * Renders the list of messages in the active conversation, or empty state with agent suggestions.
 */
function MessageList({
  messages = [],
  onSelectAttachment,
  onSendSuggestion,
  error = null,
}) {
  if (messages.length === 0) {
    return (
      <div className="empty">
        <h1>What would you like<br />to <em>know</em> today?</h1>
        <p>Attach a document or a photo, then ask by typing or by voice. Answers come only from your files, and they can be read aloud.</p>
        <div className="suggestions">
          {AGENT_SUGGESTIONS.map((s) => {
            const Icon = ICON_MAP[s.icon] || FileText;
            return (
              <button
                type="button"
                key={s.prompt}
                className="suggestion suggestion-card"
                onClick={() => onSendSuggestion && onSendSuggestion(s.prompt)}
                title={`Ask: "${s.prompt}"`}
              >
                <div className="suggestion-card-head">
                  <span className="suggestion-icon" aria-hidden="true">
                    <Icon size={18} />
                  </span>
                  <strong className="suggestion-title">{s.title}</strong>
                </div>
                <span className="suggestion-prompt">"{s.prompt}"</span>
                <small className="suggestion-desc">{s.description}</small>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div role="log" aria-label="Conversation">
      {messages.map((m) => (
        <Message
          key={m.id}
          message={m}
          onSelectAttachment={onSelectAttachment}
          onSendSuggestion={onSendSuggestion}
        />
      ))}
      {error && <p className="error-text" role="alert">{error}</p>}
    </div>
  );
}

export default memo(MessageList);
