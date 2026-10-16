import { memo } from 'react';
import UserMessage from './UserMessage';
import AssistantMessage from './AssistantMessage';

/**
 * Message
 * Dispatches to UserMessage or AssistantMessage based on role.
 */
function Message({ message, onSelectAttachment, onSendSuggestion }) {
  if (message.role === 'user') {
    return (
      <UserMessage
        content={message.content}
        attachments={message.attachments}
        onSelectAttachment={onSelectAttachment}
      />
    );
  }

  return (
    <AssistantMessage
      message={message}
      onSelectAttachment={onSelectAttachment}
      onSendSuggestion={onSendSuggestion}
    />
  );
}

export default memo(Message);
