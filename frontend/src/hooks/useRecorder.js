import { useCallback, useEffect, useRef, useState } from 'react';

export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState(null);
  const recorder = useRef(null);
  const stream = useRef(null);
  const chunks = useRef([]);
  const timer = useRef(null);

  const cleanup = useCallback(() => {
    clearInterval(timer.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    recorder.current = null;
    setRecording(false);
    setSeconds(0);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) { setError('Microphone is not supported in this browser.'); return false; }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : undefined;
      recorder.current = new MediaRecorder(stream.current, mimeType ? { mimeType } : undefined);
      chunks.current = [];
      recorder.current.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      recorder.current.start();
      setRecording(true);
      timer.current = setInterval(() => setSeconds((s) => s + 1), 1000);
      return true;
    } catch {
      setError('Microphone permission was denied.');
      cleanup();
      return false;
    }
  }, [cleanup]);

  const stop = useCallback(() => new Promise((resolve) => {
    const r = recorder.current;
    if (!r) return resolve(null);
    r.onstop = () => {
      const blob = new Blob(chunks.current, { type: r.mimeType || 'audio/webm' });
      cleanup();
      resolve(blob);
    };
    r.stop();
  }), [cleanup]);

  const cancel = useCallback(() => {
    if (recorder.current) recorder.current.onstop = null;
    try { recorder.current?.stop(); } catch { /* already stopped */ }
    cleanup();
  }, [cleanup]);

  useEffect(() => cancel, [cancel]);

  return { recording, seconds, error, start, stop, cancel };
}
