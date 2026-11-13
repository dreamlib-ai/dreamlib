import { useEffect, useRef, useState } from 'react';
import { newDraft, readDraft, writeDraft, type Draft } from './draft';
import { track } from './telemetry';
import {
  analyzeDream,
  ApiError,
  getSelfProfile,
  getJob,
  saveDream,
  startManga,
  type ArtStyle,
  type InterpretationType,
  type Perspective,
} from './api';
import Icon from './Icon';
import VoiceInput from './VoiceInput';
import Mascot from './Mascot';
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
  onProfile: () => void;
};

const styles = Object.keys(tr.styles) as ArtStyle[];
const panelCounts = [4, 6, 9];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Tell({ active, owner, inspiration, type, visibility, onLibrary, onProfile }: Props) {
  const [draft, setDraft] = useState(() => readDraft(owner) ?? newDraft());
  const { id, text, mode, analysis, style, count, panels, jobId, jobStatus, saved, recorded, personal } = draft;
  const change = (patch: Partial<Draft>) => setDraft(current => ({ ...current, ...patch }));
  const [busy, setBusy] = useState<'analyze' | 'image' | 'save' | null>(null);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [error, setError] = useState('');
  const [storageError, setStorageError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [retry, setRetry] = useState(0);
  const [feedback, setFeedback] = useState<'helpful' | 'unhelpful' | null>(null);
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
    catch (cause) { if (alive.current) setError(cause instanceof Error ? cause.message : tr.genericError); }
    finally { if (alive.current) setBusy(null); }
  }
  async function interpret() {
    const result = await run('analyze', () => analyzeDream(text, type, { personal, excludeId: id }));
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
    if (!analysis) return;
    const dream = await run('save', () => saveDream(text, type, analysis, style, panels,
      jobStatus === 'done' ? jobId : undefined, visibility, id, recorded));
    if (dream && alive.current) { change({ recorded: true, saved: true, panels: dream.panels }); track('dream_saved', id); }
  }

  return <div className={analysis ? 'tell has-result view-transition' : 'tell view-transition'}>
    {!analysis ? <>
      <header className="page-heading writer-heading"><h1>{tr.app.writingTitle}</h1></header>
      {busy === 'analyze' ? <section className="dream-processing" role="status"><Mascot theme="sleep" /><p>{tr.capture.analyzing}</p></section> : mode === 'voice' ? <section className="voice-stage">
        <Mascot theme="curious" interactive className="listening-koala" />
        <VoiceInput active={active} onBusy={setVoiceBusy} disabled={busy !== null} onText={(transcript) => { setDraft(d => ({ ...d, text: `${d.text}${d.text ? '\n' : ''}${transcript}`, mode: 'text' })); }} onError={setError} />
        <button className="text-action input-switch" disabled={voiceBusy} onClick={() => { setError(''); change({ mode: 'text' }); }}><Icon name="pen" />{tr.capture.write}</button>
      </section> : <section className="writing-sheet">
        <textarea autoFocus aria-label={tr.headline} aria-invalid={text.length > 4000} aria-describedby={text.length > 4000 ? 'dream-length' : undefined} value={text} onChange={(event) => change({ text: event.target.value, saved: false })} placeholder={tr.writePlaceholder} rows={8} />
        {text.length > 4000 && <p id="dream-length" className="error">{tr.capture.tooLong}</p>}
        <div className="personal-setting"><label><input type="checkbox" checked={personal} onChange={event => change({ personal: event.target.checked })} aria-describedby={personal ? "personal-hint" : undefined} /><span>{tr.personal.label}</span></label>
          {personal && <p id="personal-hint">{tr.personal.hint}</p>}</div>
        <div className="composer-tools"><button className="text-action" onClick={() => { setError(''); setVoiceBusy(false); change({ mode: 'voice' }); }}><Icon name="mic" />{tr.app.voice}</button>
          <button className="send-dream" aria-label={tr.capture.send} title={tr.capture.send} disabled={!text.trim() || text.length > 4000} onClick={() => void interpret()}><Icon name="send" /></button></div>
      </section>}
    </> : <>
      <header className="result-heading"><button className="back" disabled={busy !== null || jobStatus === 'pending'} aria-label={tr.app.edit} onClick={() => change({ analysis: null })}><Icon name="chevron" /></button><span>{tr.headline}</span></header>
      <div className="result-sheet"><Result analysis={analysis} key={analysis.title}>
        <div className="result-feedback" role="group" aria-label={tr.feedback.question}><span>{tr.feedback.question}</span>
          {(['helpful', 'unhelpful'] as const).map(value => <button key={value} className="text-action" aria-pressed={feedback === value} onClick={() => { setFeedback(value); track(value === 'helpful' ? 'feedback_helpful' : 'feedback_unhelpful', id); }}>{value === 'helpful' ? tr.feedback.yes : tr.feedback.no}</button>)}
        </div>
        <section className="booklet-settings"><details className="drawing-options"><summary>{tr.app.settings}</summary>
          <div className="chips">{styles.map((item) => <button key={item} aria-pressed={style === item} className={style === item ? 'chip on' : 'chip'} disabled={busy !== null || jobStatus === 'pending'} onClick={() => change({ style: item })}>{tr.styles[item]}</button>)}</div>
          <div className="chips">{panelCounts.map((item) => <button key={item} aria-pressed={count === item} className={count === item ? 'chip on' : 'chip'} disabled={busy !== null || jobStatus === 'pending'} onClick={() => change({ count: item })}>{tr.panelCount(item)}</button>)}</div>
          <label className="avatar-toggle"><input type="checkbox" checked={draft.useAvatar} disabled={busy!==null||jobStatus==='pending'} onChange={e=>change({useAvatar:e.target.checked})} />{tr.avatar.useInDream}</label>
          <label className="drawing-camera">{tr.avatar.camera}<select value={draft.perspective} disabled={busy!==null||jobStatus==='pending'} onChange={e=>change({perspective:e.target.value as Perspective})}>{(['unknown','first-person','observer','mixed'] as const).map(value=><option key={value} value={value}>{value==='unknown'?tr.avatar.automatic:tr.classification.perspectiveLabels[value]}</option>)}</select></label>
          <button className="text-action" disabled={busy!==null||jobStatus==='pending'} onClick={onProfile}>{tr.avatar.create}</button>
          </details><div className="actions"><button className="go" disabled={busy !== null} onClick={() => jobStatus === 'pending' ? setRetry(n => n + 1) : visualize()}>{busy === 'image' ? tr.app.progress : jobStatus === 'pending' ? tr.recovery.resume : tr.visualize}</button>
            {saved ? <button className="go quiet" onClick={onLibrary}>{tr.openLibrary}</button> : <button className="go quiet" disabled={busy !== null || jobStatus === 'pending'} onClick={() => void save()}>{busy === 'save' ? tr.saving : tr.save}</button>}
          </div>
        </section>
        {busy === 'image' && <div className="drawing-progress" role="status"><progress max={count} value={progress} /><span>{tr.app.progress}</span></div>}
        {panels.length > 0 && <section className="booklet"><h3>{tr.app.artwork}</h3><div className="shots">{panels.map((panel) => <figure key={panel.path}>{panel.url && <img src={panel.url} alt={panel.caption} />}{panel.caption && <figcaption>{panel.caption}</figcaption>}</figure>)}</div></section>}
      </Result></div>
    </>}
    {storageError && <p className="error" role="status">{tr.recovery.storage}</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
