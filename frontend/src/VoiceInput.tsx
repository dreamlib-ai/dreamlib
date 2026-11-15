import { useEffect, useRef, useState } from 'react';
import { track } from './telemetry';
import { transcribeAudio } from './api';
import { DreamRecorder } from './recorder';
import Icon from './Icon';
import { tr } from './strings';

export default function VoiceInput({ active, disabled, onText, onError, onBusy }: { active: boolean; disabled: boolean; onText: (text: string) => void; onError: (error: string) => void; onBusy: (busy: boolean) => void }) {
  const [state, setState] = useState<'idle' | 'requesting' | 'recording' | 'transcribing'>('idle');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [retryAudio, setRetryAudio] = useState<Blob | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const mounted = useRef(false);
  const request = useRef(0);
  const recordingId = useRef('');
  const pending = useRef<AbortController | null>(null);
  const callbacks = useRef({ onText, onError });
  callbacks.current = { onText, onError };
  const [recorder] = useState(() => new DreamRecorder({
    onState: (next, media) => { if (mounted.current) {
      if (next === 'recording') { recordingId.current = crypto.randomUUID(); track('record_started', recordingId.current); }
      setState(next); setStream(media);
    } },
    onAudio: audio => { void transcribe(audio); },
    onError: error => { if (mounted.current) callbacks.current.onError(error === 'unsupported' ? tr.app.audioUnsupported : error === 'empty' ? tr.capture.empty : error === 'limit' ? tr.app.audioTooLarge : tr.app.microphoneError); },
  }));
  async function transcribe(audio: Blob) {
    const id = ++request.current;
    if (!mounted.current) return;
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 60_000);
    setState('transcribing'); setRetryAudio(audio); callbacks.current.onError('');
    try {
      const text = await transcribeAudio(audio, 'tr', controller.signal);
      if (mounted.current && id === request.current) {
        if (!text.trim()) { callbacks.current.onError(tr.capture.empty); return; }
        setRetryAudio(null); track('transcript_ready', recordingId.current); callbacks.current.onText(text);
      }
    } catch {
      if (mounted.current && id === request.current) callbacks.current.onError(tr.capture.failed);
    } finally { window.clearTimeout(timeout); if (mounted.current && id === request.current) { pending.current = null; setState('idle'); } }
  }
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; ++request.current; pending.current?.abort(); recorder.cancel(); };
  }, [recorder]);
  useEffect(() => {
    if (!active) {
      if (state === 'recording') recorder.finish();
      else if (state === 'requesting') recorder.cancel();
    }
  }, [active, recorder, state]);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  useEffect(() => { onBusy(state !== 'idle'); }, [state, onBusy]);
  useEffect(() => {
    if (state !== 'recording') { setSeconds(0); return; }
    const started = Date.now();
    const timer = window.setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 250);
    return () => window.clearInterval(timer);
  }, [state]);
  useEffect(() => {
    const stop = () => {
      if (!document.hidden) return;
      if (state === 'recording') recorder.finish();
      else if (state === 'requesting') recorder.cancel();
    };
    document.addEventListener('visibilitychange', stop);
    return () => document.removeEventListener('visibilitychange', stop);
  }, [recorder, state]);
  useEffect(() => {
    if (state === 'idle') return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [state]);
  // The orb breathes with the voice: the microphone's loudness becomes --level (0..1) on the orb.
  const orb = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const node = orb.current;
    if (!stream || reducedMotion || !node) { node?.style.setProperty('--level', '0'); return; }
    const context = new AudioContext(); void context.resume();
    const analyser = context.createAnalyser(); analyser.fftSize = 512;
    context.createMediaStreamSource(stream).connect(analyser);
    const samples = new Uint8Array(analyser.fftSize);
    let level = 0, frame = 0;
    const tick = () => {
      analyser.getByteTimeDomainData(samples);
      let sum = 0; for (const s of samples) sum += ((s - 128) / 128) ** 2;
      level = level * 0.82 + Math.min(1, Math.sqrt(sum / samples.length) * 5) * 0.18;
      node.style.setProperty('--level', level.toFixed(3));
      frame = requestAnimationFrame(tick);
    };
    tick();
    return () => { cancelAnimationFrame(frame); node.style.setProperty('--level', '0'); void context.close(); };
  }, [stream, reducedMotion]);
  const processing = state === 'requesting' || state === 'transcribing';
  const label = state === 'recording' ? tr.app.stop : state === 'requesting' ? tr.capture.permission : state === 'transcribing' ? tr.app.transcribing : tr.app.voice;
  const cancel = () => { ++request.current; pending.current?.abort(); recorder.cancel(); setRetryAudio(null); callbacks.current.onError(''); };
  return <div className="voice-capture" aria-busy={processing}>
    <button ref={orb} className={`orb orb-${state}`} aria-label={label} title={label} disabled={disabled || processing} onClick={() => {
      if (state === 'recording') { recorder.finish(); return; }
      setRetryAudio(null); callbacks.current.onError(''); void recorder.start();
    }}>
      <span className="orb-sky" aria-hidden="true"><i /><i /></span>
      <span className="orb-icon"><Icon name={state === 'recording' ? 'stop' : processing ? 'loader' : 'mic'} /></span>
    </button>
    <div className="capture-status" role={state === 'recording' ? 'timer' : 'status'} aria-live={state === 'recording' ? 'off' : 'polite'}>{state === 'recording' ? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}` : state === 'transcribing' ? tr.app.transcribing : state === 'requesting' ? tr.capture.permission : retryAudio ? '' : tr.app.voice}</div>
    {state !== 'idle' && <button className="text-action capture-cancel" onClick={cancel}>{tr.library.cancel}</button>}
    {retryAudio && state === 'idle' && <div className="capture-retry"><button className="text-action" onClick={() => void transcribe(retryAudio)}>{tr.app.retry}</button><button className="text-action" onClick={cancel}>{tr.library.cancel}</button></div>}
  </div>;
}
