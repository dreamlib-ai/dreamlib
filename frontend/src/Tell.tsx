import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { newDraft, readDraft, writeDraft, type Draft } from './draft';
import { track } from './telemetry';
import {
  ApiError,
  streamDream,
  type StreamProgress,
  getSelfProfile,
  getJob,
  listDreamPage,
  saveDream,
  type Dream,
  startManga,
  type InterpretationType,
} from './api';
import Drawing from './Drawing';
import Icon from './Icon';
import Mascot, { type Pose } from './Mascot';
import Orb from './Orb';
import VoiceInput from './VoiceInput';
import Worn from './Worn';
import type { Visibility } from './profile';
import Result from './Result';
import { tr } from './strings';

type Props = {
  active: boolean;
  owner: string;
  inspiration?: string;
  type: InterpretationType;
  visibility: Visibility;
  onType: (t: InterpretationType) => void;
  onLibrary: () => void;
  /** The way back from the reading to the told dream lives in the top bar; null hides it. */
  onBack: (back: (() => void) | null) => void;
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Tell({ active, owner, inspiration, type, visibility, onLibrary, onBack }: Props) {
  const [draft, setDraft] = useState(() => readDraft(owner) ?? newDraft());
  const { id, text, mode, analysis, style, count, panels, jobId, jobStatus, saved, recorded } = draft;  // past dreams are always used when they relate (Cenker, 2026-11-15)
  const change = (patch: Partial<Draft>) => setDraft(current => ({ ...current, ...patch }));
  const [busy, setBusy] = useState<'analyze' | 'image' | 'save' | null>(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [error, setError] = useState('');
  const [saveError, setSaveError] = useState<{ message: string; retryable: boolean } | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [eta, setEta] = useState<number | undefined>();
  const [retry, setRetry] = useState(0);
  const [feedback, setFeedback] = useState<'helpful' | 'unhelpful' | null>(null);
  const [writing, setWriting] = useState<StreamProgress | null>(null);
  const alive = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => { setStorageError(!writeDraft(owner, draft)); }, [owner, draft]);
  useEffect(() => {
    if (inspiration) setDraft(current => current.text.trim() ? current : { ...current, text: inspiration });
  }, [inspiration]);

  // The request id is persisted before any network call. Replays return the same job.
  useEffect(() => {
    if (!active || !jobId || !analysis || jobStatus === 'failed') return;
    const controller = new AbortController();
    let current = true;
    const follow = async () => {
      if (jobStatus === 'pending') { setBusy('image'); setError(''); }
      try {
        if (jobStatus === 'pending') await startManga(analysis.title, analysis.cleanText, style, count, true, jobId, controller.signal,
          {useAvatar:draft.jobUseAvatar,avatarRevision:draft.jobAvatarRevision,perspective:draft.jobPerspective});
        let failures = 0;
        for (;;) {
          let job;
          try {
            job = await getJob(jobId, controller.signal);
            failures = 0;
          } catch (cause) {
            if (controller.signal.aborted || ++failures >= 3) throw cause;
            await sleep(1500);
            if (!current) return;
            continue;
          }
          if (!current) return;
          setProgress(job.done);
          setEta(job.etaSeconds);
          if (job.status === 'done') {
            if (jobStatus === 'pending') track('booklet_ready', jobId);
            setDraft(d => ({ ...d, panels: job.panels, jobStatus: 'done' }));
            return;
          }
          if (job.status === 'failed') {
            setDraft(d => ({ ...d, jobStatus: 'failed' }));
            throw new Error(job.error || tr.genericError);
          }
          await sleep(2000);
          if (!current) return;
        }
      } catch (cause) {
        if (current && !controller.signal.aborted) {
          if(cause instanceof ApiError && [400,404,409].includes(cause.status))setDraft(d=>({...d,jobStatus:'failed'}));
          setError(cause instanceof TypeError ? tr.recovery.connection : cause instanceof Error ? cause.message : tr.genericError);
        }
      } finally { if (current) setBusy(null); }
    };
    // Completed jobs only need signed URLs refreshed once after restoring a draft.
    if (jobStatus === 'done' && panels.every(p => p.url)) return;
    void follow();
    return () => { current = false; controller.abort(); };
  }, [active, jobId, jobStatus, retry]);

  async function run<T>(kind: 'analyze' | 'save', work: () => Promise<T>): Promise<T | undefined> {
    setBusy(kind); setError('');
    try { return await work(); }
    catch (cause) {
      if (alive.current && kind === 'save') {
        const retryable = !(cause instanceof ApiError) || cause.status === 408 || cause.status === 429 || cause.status >= 500;
        setSaveError({
          message: !retryable && cause instanceof ApiError ? cause.message : tr.recovery.saveFailed,
          retryable,
        });
      } else if (alive.current) {
        setError(cause instanceof Error ? cause.message : tr.genericError);
      }
    }
    finally { if (alive.current) setBusy(null); }
  }
  async function interpret() {
    setSaveError(null);
    setWriting(null);
    const calm = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;  // then the text comes at once
    const result = await run('analyze', () => streamDream(text, type, { personal: true, excludeId: id },
      (progress) => { if (alive.current && !calm) setWriting(progress); }));
    if (alive.current) setWriting(null);
    if (result && alive.current) {
      change({ analysis: result, panels: [], jobId: undefined, jobStatus: 'none', saved: false });
      setFeedback(null); track('analysis_ready', id);
    }
  }
  async function visualize() {
    if (!analysis || busy) return;
    setError(''); setProgress(0);setBusy('image');
    try {
      const profile=draft.useAvatar?await getSelfProfile():null;
      const useAvatar=!!profile?.avatar && draft.useAvatar;
      change({ jobId: crypto.randomUUID(), jobStatus: 'pending', saved: false,
        jobUseAvatar:useAvatar,jobAvatarRevision:useAvatar?profile!.revision:0,
        jobPerspective:draft.perspective==='unknown'?analysis.features?.perspective??'unknown':draft.perspective });
    } catch(cause) { setBusy(null);setError(cause instanceof Error?cause.message:tr.genericError); }
  }
  async function save() {
    if (!analysis || busy !== null || jobStatus === 'pending') return;
    setSaveError(null);
    const dream = await run('save', () => saveDream(text, type, analysis, style, panels,
      jobStatus === 'done' ? jobId : undefined, visibility, id, recorded));
    if (dream && alive.current) { change({ recorded: true, saved: true, panels: dream.panels }); track('dream_saved', id); }
  }
  // The dream keeps itself: once when the reading arrives and once more when its pictures are drawn.
  const autosaved = useRef('');
  const saveKey = analysis ? `${analysis.title}:${jobStatus}:${panels.length}` : '';
  useEffect(() => {
    if (!active || !analysis || saved || busy !== null || jobStatus === 'pending' || autosaved.current === saveKey) return;
    autosaved.current = saveKey;
    void save();
  }, [active, saveKey, saved, busy]);
  useEffect(() => {
    if (!active) return;
    onBack(analysis && busy === null && jobStatus !== 'pending' ? () => { setError(''); change({ analysis: null }); } : null);
    return () => onBack(null);
  }, [active, !!analysis, busy, jobStatus]);
  const [justDone, setJustDone] = useState(false);  // the koala cheers when the reading lands, then settles
  useEffect(() => {
    if (busy !== 'analyze') return;
    return () => { setJustDone(true); setTimeout(() => alive.current && setJustDone(false), 4000); };
  }, [busy]);
  const pose: Pose = busy === 'analyze' ? 'think' : busy === 'image' ? 'hold' : justDone || jobStatus === 'done' ? 'joy' : 'curious';
  // Writing folds away when the dreamer looks up: the field becomes one line and the orb rises above it.
  const [settled, setSettled] = useState(false);
  const sheet = useRef<HTMLElement>(null);
  useEffect(() => { if (!text.trim()) setSettled(false); }, [text]);
  useEffect(() => { if (mode !== 'text') setSettled(false); }, [mode]);
  const lookUp = () => window.setTimeout(() => { if (alive.current && !sheet.current?.contains(document.activeElement)) setSettled(true); }, 0);
  // A tap anywhere else folds the field away, whether or not the textarea still had the focus.
  useEffect(() => {
    if (!active || mode !== 'text' || settled || !text.trim()) return;
    const away = (event: PointerEvent) => { if (!sheet.current?.contains(event.target as Node)) setSettled(true); };
    document.addEventListener('pointerdown', away, true);
    return () => document.removeEventListener('pointerdown', away, true);
  }, [active, mode, settled, text]);

  return <div className={analysis ? 'tell has-result view-transition' : 'tell view-transition'}>
    {(busy === 'analyze' || analysis) && <Mascot pose={pose} className="reading-koala" />}
    {!analysis ? <>
      {busy !== 'analyze' && <header className="tell-heading"><h1><Worn text={tr.app.writingTitle} /></h1></header>}
      {busy === 'analyze' ? writing && (writing.title || writing.text) ? <Writing progress={writing} /> : <section className="dream-processing" role="status"><p>{tr.capture.analyzing}</p>{writing && writing.symbols.length > 0 && <SymbolRow symbols={writing.symbols} />}</section> : mode === 'voice' ? <section className="voice-stage">
        <VoiceInput active={active} onBusy={setVoiceBusy} disabled={busy !== null} onText={(transcript) => { setDraft(d => ({ ...d, text: `${d.text}${d.text ? '\n' : ''}${transcript}`, mode: 'text' })); }} onError={setError} />
        {!voiceBusy && <RecentDreams active={active} onLibrary={onLibrary} />}
        {!voiceBusy && active && createPortal(<button className="dream-bar" onClick={() => { setError(''); change({ mode: 'text' }); }}><span>{tr.writePlaceholder}</span><Icon name="pen" /></button>, document.body)}
      </section> : active ? createPortal(settled ? <>
        <button className="orb settled-orb" aria-label={tr.app.voice} title={tr.app.voice} onClick={() => { setError(''); change({ mode: 'voice' }); }}>
          <span className="orb-sky" aria-hidden="true"><i /><i /></span>
          <Orb />
        </button>
        <section ref={sheet} className="composer settled" aria-label={tr.capture.write}>
          <button className="settled-text" onClick={() => { setError(''); setSettled(false); }}>{text}</button>
          <div className="composer-tools">
            <button className="composer-close" aria-label={tr.app.voice} title={tr.app.voice} onClick={() => { setError(''); change({ mode: 'voice' }); }}><Icon name="mic" /></button>
            <button className="send-dream" aria-label={tr.capture.send} title={tr.capture.send} disabled={!text.trim() || text.length > 4000} onClick={() => void interpret()}><Icon name="send" /></button>
          </div>
        </section>
      </> : <section ref={sheet} className="writing-sheet composer" aria-label={tr.capture.write} onBlur={lookUp}>
        <textarea autoFocus aria-label={tr.headline} aria-invalid={text.length > 4000} aria-describedby={text.length > 4000 ? 'dream-length' : undefined} value={text} onChange={(event) => change({ text: event.target.value, saved: false })} placeholder={tr.writePlaceholder} rows={8} />
        {text.length > 4000 && <p id="dream-length" className="error">{tr.capture.tooLong}</p>}
        <div className="composer-tools"><button className="composer-close" aria-label={tr.app.voice} title={tr.app.voice} onClick={() => { setError(''); change({ mode: 'voice' }); }}><Icon name="mic" /></button>
          <button className="send-dream" aria-label={tr.capture.send} title={tr.capture.send} disabled={!text.trim() || text.length > 4000} onClick={() => void interpret()}><Icon name="send" /></button></div>
      </section>, document.body) : null}
    </> : <>
      <div className="result-sheet"><Result analysis={analysis} key={analysis.title} traces={false} after={
        <>
          <div className="reading-save">
            <span role="status">{busy === 'save' ? tr.recovery.saving : saved ? tr.app.savedDream : ''}</span>
            {saveError && <div className="reading-save-error">
              <p role="alert">{saveError.message}</p>
              {saveError.retryable && <button className="text-action" disabled={busy !== null || jobStatus === 'pending'} onClick={() => void save()}>{tr.app.retry}</button>}
            </div>}
          </div>
          <div className="result-feedback" role="group" aria-label={tr.feedback.question}><span>{tr.feedback.question}</span>
            {(['helpful', 'unhelpful'] as const).map(value => <button key={value} className="text-action" aria-pressed={feedback === value} onClick={() => { setFeedback(value); track(value === 'helpful' ? 'feedback_helpful' : 'feedback_unhelpful', id); }}>{value === 'helpful' ? tr.feedback.yes : tr.feedback.no}</button>)}
          </div>
        </>}>
        {busy === 'image' ? <Drawing count={count} done={progress} eta={eta} />
          : !(jobStatus === 'done' && panels.length > 0) && <button className="cloud-button visualize" disabled={busy !== null} onClick={() => jobStatus === 'pending' ? setRetry(n => n + 1) : void visualize()}>
            <span className="cloud-fill" aria-hidden="true"><i /><i /></span><span className="cta-label">{jobStatus === 'pending' ? tr.recovery.resume : tr.visualize}</span></button>}
        {panels.length > 0 && <section className="booklet"><div className="shots">{panels.map((panel) => <figure key={panel.path}>{panel.url && <Sharpen src={panel.url} alt={panel.caption} />}{panel.caption && <figcaption>{panel.caption}</figcaption>}</figure>)}</div></section>}
      </Result></div>
    </>}
    {storageError && <p className="error" role="status">{tr.recovery.storage}</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}

// G8: the interpretation as it is written; the symbols the dream names sit above it with their icons.
const dayOf = (dream: Dream) => new Date(dream.journal?.dreamedOn ? dream.journal.dreamedOn + 'T12:00:00' : dream.createdAt)
  .toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' });

/** The last few dreams under the record button, so the first screen also leads back to what was told before. */
function RecentDreams({ active, onLibrary }: { active: boolean; onLibrary: () => void }) {
  const [dreams, setDreams] = useState<Dream[]>([]);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    listDreamPage(undefined, 3, controller.signal).then(page => setDreams(page.dreams)).catch(() => {});
    return () => controller.abort();
  }, [active]);
  if (!dreams.length) return null;
  return <section className="recent" aria-labelledby="recent-title">
    <header><h2 id="recent-title">{tr.app.recent}</h2><button className="quiet-link" onClick={onLibrary}>{tr.app.all}</button></header>
    <ul>{dreams.map(dream => <li key={dream.id}><button onClick={onLibrary}>
      <time>{dayOf(dream)}</time><span>{dream.title}</span>
    </button></li>)}</ul>
  </section>;
}

/** A drawn panel comes into focus: blurred while it loads, then sharpens. */
function Sharpen({ src, alt }: { src: string; alt: string }) {
  const [shown, setShown] = useState(false);
  return <img src={src} alt={alt} className={shown ? 'sharpen in' : 'sharpen'} onLoad={() => setShown(true)} />;
}

function Writing({ progress }: { progress: StreamProgress }) {
  return <section className="result writing" aria-busy="true" aria-live="polite">
    {progress.symbols.length > 0 && <SymbolRow symbols={progress.symbols} />}
    {progress.title && <h2>{progress.title}</h2>}
    <p className="lead">{progress.text}<span className="caret" aria-hidden="true" /></p>
  </section>;
}

function SymbolRow({ symbols }: { symbols: StreamProgress['symbols'] }) {
  return <ul className="symbol-row" aria-label={tr.symbols.found}>
    {symbols.map((s) => <li key={s.id}>{s.glyph && <img src={s.glyph} alt="" />}<span>{s.text}</span></li>)}
  </ul>;
}
