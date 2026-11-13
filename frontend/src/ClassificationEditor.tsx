import { useState } from 'react';
import type { ClassificationOverride, Dream, JournalPatch, Perspective } from './api';
import { effectiveFeatures, experiences, genres, perspectives } from './features';
import { tr } from './strings';

const text = tr.classification;
const same = (a: string[], b: string[]) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
const toggled = <T,>(items: T[], value: T) => items.includes(value) ? items.filter(item => item !== value) : [...items, value];

export default function ClassificationEditor({ dream, disabled, onSave }: { dream: Dream; disabled: boolean; onSave: (changes: JournalPatch) => Promise<boolean> }) {
  const current = effectiveFeatures(dream);
  const initial = () => ({ genres: current.genres, experiences: current.experiences, perspective: current.perspective, tags: current.tags.join(', '), recall: dream.journal?.recall ?? '' });
  const [form, setForm] = useState(initial);
  const [open, setOpen] = useState(false);
  async function save() {
    const override: ClassificationOverride = { ...dream.journal?.classification };
    if (!same(form.genres, current.genres)) override.genres = form.genres;
    if (!same(form.experiences, current.experiences)) override.experiences = form.experiences;
    if (form.perspective !== current.perspective) override.perspective = form.perspective;
    const tags = [...new Set(form.tags.split(',').map(tag => tag.trim()).filter(Boolean))];
    if (!same(tags, current.tags)) override.tags = tags;
    if (await onSave({ classification: Object.keys(override).length ? override : null, recall: form.recall })) setOpen(false);
  }
  return <details className="classification-editor" open={open} onToggle={event => {
    const next = event.currentTarget.open;
    if (next && !open) setForm(initial());
    setOpen(next);
  }}><summary>{text.correct}</summary><form className="journal-form" onSubmit={event => { event.preventDefault(); void save(); }}>
    {current.version === 0 && <button type="button" className="text-action" disabled={disabled} onClick={() => void onSave({refresh:true}).then(ok => { if (ok) setOpen(false); })}>{text.extract}</button>}
    <fieldset disabled={disabled}><legend>{text.genres}</legend><div className="classification-choices">{genres.map(key => <label key={key}><input type="checkbox" checked={form.genres.includes(key)} onChange={() => setForm({ ...form, genres:toggled(form.genres,key) })} />{text.genreLabels[key]}</label>)}</div></fieldset>
    <fieldset disabled={disabled}><legend>{text.experiences}</legend><div className="classification-choices">{experiences.map(key => <label key={key}><input type="checkbox" checked={form.experiences.includes(key)} onChange={() => setForm({ ...form, experiences:toggled(form.experiences,key) })} />{text.experienceLabels[key]}</label>)}</div></fieldset>
    <label>{text.perspective}<select disabled={disabled} value={form.perspective} onChange={e => setForm({ ...form, perspective:e.target.value as Perspective })}>{perspectives.map(key => <option key={key} value={key}>{text.perspectiveLabels[key]}</option>)}</select></label>
    <label>{text.tags}<input disabled={disabled} maxLength={1600} value={form.tags} onChange={e => setForm({ ...form, tags:e.target.value })} /></label>
    <label>{text.recall}<select disabled={disabled} value={form.recall} onChange={e => setForm({ ...form, recall:e.target.value as typeof form.recall })}>{Object.entries(text.recallLabels).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
    <div className="journal-actions"><button className="go" disabled={disabled}>{tr.journal.save}</button><button type="button" className="text-action" disabled={disabled || !dream.journal?.classification} onClick={() => void onSave({classification:null}).then(ok => { if (ok) setOpen(false); })}>{text.reset}</button></div>
  </form></details>;
}
