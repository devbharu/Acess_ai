import { memo } from 'react';
import { Loader2, Square, Volume2 } from 'lucide-react';
import { speechStore } from '../audio/speech';
import { useSpeechState } from '../hooks/useSpeech';
import { useSettings } from '../context/SettingsContext';

/**
 * AudioPlayer
 * Provides accessible text-to-speech playback controls for messages and text passages.
 */
function AudioPlayer({ id, text, className = '' }) {
  const { settings } = useSettings();
  const state = useSpeechState(id);
  const isPlaying = state === 'playing';
  const isLoading = state === 'loading';

  const onClick = () => {
    speechStore.speak(id, text, {
      voice: settings.tts_voice,
      speed: settings.tts_speed,
    });
  };

  const label = isPlaying ? 'Stop reading' : isLoading ? 'Preparing audio' : 'Read aloud';

  return (
    <button
      type="button"
      className={`chat-action-btn ${isPlaying ? 'active' : ''} ${className}`}
      onClick={onClick}
      aria-label={label}
      title={label}
    >
      {isLoading ? (
        <Loader2 size={16} className="spin" />
      ) : isPlaying ? (
        <Square size={13} fill="currentColor" />
      ) : (
        <Volume2 size={16} />
      )}
    </button>
  );
}

export default memo(AudioPlayer);
