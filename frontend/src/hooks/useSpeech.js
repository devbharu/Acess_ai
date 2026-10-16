import { useSyncExternalStore } from 'react';
import { speechStore } from '../audio/speech';

export function useSpeechState(key) {
  return useSyncExternalStore(speechStore.subscribe, () => speechStore.stateFor(key));
}
