import { useState } from 'react';
import { editJournal, type Dream, type JournalPatch } from './api';
import Icon from './Icon';
import VoiceInput from './VoiceInput';
import { tr } from './strings';
import ClassificationEditor from './ClassificationEditor';

const text = tr.journal;
const localDate = () => new Date().toLocaleDateString('sv-SE');

export default function JournalEditor({ dream, onUpdated }: { dream: Dream; onUpdated: (dream: Dream) => void }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ title: dream.title, originalText: dream.originalText, dreamedOn: dream.journal?.dreamedOn ?? '', reflection: dream.journal?.reflection ?? '' });
  const [addition, setAddition] = useState('');
  const [additionId, setAdditionId] = useState(() => crypto.randomUUID());
  const [voice, setVoice] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [personal, setPersonal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function save(changes: JournalPatch): Promise<boolean> {
    setBusy(true); setError('');
    try { onUpdated(await editJournal(dream, changes)); return true; }
    catch (cause) { setError(cause instanceof Error ? cause.message : tr.genericError); return false; }
    finally { setBusy(false); }
  }
  return <section className="journal-editor" aria-label={text.heading} aria-busy={busy}>
    <div className="journal-actions">
      <button className="text-action" disabled={busy || editing || voiceBusy} aria-pressed={dream.journal?.favorite ?? false} onClick={() => void save({ favorite: !dream.journal?.favorite })}><Icon name="heart" />{dream.journal?.favorite ? text.favorited : text.favorite}</button>
      <button className="text-action" disabled={busy || voiceBusy} onClick={() => {
        if (!editing) setForm({ title: dream.title, originalText: dream.originalText, dreamedOn: dream.journal?.dreamedOn ?? '', reflection: dream.journal?.reflection ?? '' });
        setEditing(value => !value);
      }}><Icon name="pen" />{editing ? tr.library.cancel : tr.app.edit}</button>
    </div>
    {editing && <form className="journal-form" onSubmit={event => { event.preventDefault(); void save({ ...form, dreamedOn: form.dreamedOn || null }).then(ok => { if (ok) setEditing(false); }); }}>
      <label>{text.title}<input required maxLength={200} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
      <label>{text.date}<input type="date" max={localDate()} value={form.dreamedOn} onInput={e => { const value = e.currentTarget.value; setForm(current => ({ ...current, dreamedOn: value })); }} /></label>
      <label>{tr.app.original}<textarea required maxLength={4000} value={form.originalText} onChange={e => setForm({ ...form, originalText: e.target.value })} /></label>
      <label>{text.reflection}<textarea maxLength={4000} value={form.reflection} placeholder={text.reflectionPlaceholder} onChange={e => setForm({ ...form, reflection: e.target.value })} /></label>
      <button className="go" disabled={busy}>{busy ? tr.saving : text.save}</button>
    </form>}
    {!editing && dream.journal?.reflection && <section className="journal-reflection"><h3>{text.reflection}</h3><p>{dream.journal.reflection}</p></section>}
    <ClassificationEditor dream={dream} disabled={busy || editing || voiceBusy} onSave={save} />
    {dream.journal?.firstText && <details className="original-dream"><summary>{text.firstText}</summary><p>{dream.journal.firstText}</p></details>}
    {(dream.journal?.entries ?? []).map(entry => <div className="journal-entry" key={entry.id}><time dateTime={entry.createdAt}>{new Date(entry.createdAt).toLocaleString('tr-TR')}</time><p>{entry.text}</p></div>)}
    <details className="journal-addition" onToggle={event => setDetailOpen(event.currentTarget.open)}><summary>{text.addDetail}</summary>
      <label><span className="sr">{text.addDetail}</span><textarea maxLength={4000} value={addition} placeholder={text.detailPlaceholder} onChange={e => { setAddition(e.target.value); setAdditionId(crypto.randomUUID()); }} /></label>
      <div className="journal-actions"><button className="text-action" aria-label={tr.app.voice} aria-expanded={voice} disabled={busy || voiceBusy} onClick={() => setVoice(value => !value)}><Icon name="mic" /></button>
        <button className="go" disabled={busy || voiceBusy || !addition.trim() || addition.length > 4000} onClick={() => void save({ addition: { id: additionId, text: addition } }).then(ok => { if (ok) { setAddition(''); setAdditionId(crypto.randomUUID()); setVoice(false); } })}>{text.add}</button></div>
      {voice && <VoiceInput active={detailOpen} disabled={busy} onText={value => { setAddition(current => [current, value].filter(Boolean).join('\n')); setAdditionId(crypto.randomUUID()); }} onError={setError} onBusy={setVoiceBusy} />}
    </details>
    {dream.journal?.analysisStale && <div className="journal-refresh"><p>{text.stale}</p><label className="personal-setting"><input type="checkbox" checked={personal} disabled={busy} onChange={e => setPersonal(e.target.checked)} />{tr.personal.label}</label>{personal && <p>{tr.personal.hint}</p>}<button className="text-action" disabled={busy || editing || voiceBusy} onClick={() => void save({ refresh: true, personal })}>{busy ? tr.capture.analyzing : text.refresh}</button></div>}
    {dream.journal?.artStale && <p className="small">{text.artStale}</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
