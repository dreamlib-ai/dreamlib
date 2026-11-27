import { useEffect, useRef, useState } from 'react';
import AccountData from './AccountData';
import Icon from './Icon';
import { ApiError, createAvatar, getJob, getSelfProfile, updateSelfProfile, type AvatarProfile } from './api';
import {
  appearanceOptions, clearAvatarDesign, clearAvatarDraft, defaultAvatar, presetIds,
  readAvatarDesign, readAvatarDraft, writeAvatarDesign, writeAvatarDraft,
  type AvatarSpec, type PresetId,
} from './avatar';
import { tr } from './strings';
import './avatar.css';

const text = tr.avatar;
const groups = {
  face: ['skin', 'face', 'expression'],
  hair: ['hair', 'hairColor'],
  clothes: ['outfit', 'outfitColor', 'accessory'],
  pose: ['build', 'pose'],
} as const satisfies Record<string, readonly (keyof AvatarSpec)[]>;
type Group = keyof typeof groups;
const colors: Partial<Record<keyof AvatarSpec, Record<string, string>>> = {
  skin: { light: '#eed2bb', warm: '#c78b65', olive: '#aa795a', deep: '#684332' },
  hairColor: { brown: '#63443a', black: '#252531', copper: '#b7644b', blond: '#dbb879', grey: '#a0a3ad' },
  outfitColor: { midnight: '#27223e', sage: '#93a792', cobalt: '#5b72be', cream: '#e8d9ba' },
};

export default function AvatarPage({ owner, onUpdated }: { owner: string; onUpdated: (profile: AvatarProfile) => void }) {
  const [profile, setProfile] = useState<AvatarProfile | null>(null);
  const [pending, setPending] = useState(() => readAvatarDraft(owner));
  const [form, setForm] = useState(() => readAvatarDesign(owner) ?? pending?.spec ?? defaultAvatar);
  const [editing, setEditing] = useState(() => !!(readAvatarDesign(owner) ?? pending));
  const [group, setGroup] = useState<Group>('face');
  const [name, setName] = useState('');
  const [preset, setPreset] = useState<PresetId | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [preview, setPreview] = useState('');
  const [working, setWorking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [storageError, setStorageError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [load, setLoad] = useState(0);
  const previewRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!preview) return;
    const candidate = previewRef.current;
    candidate?.focus({ preventScroll: true });
    candidate?.scrollIntoView({ block: 'start' });
  }, [preview]);

  useEffect(() => {
    let alive = true;
    getSelfProfile().then(value => {
      if (!alive) return;
      setProfile(value);
      setName(value.displayName);
      setForm(readAvatarDesign(owner) ?? readAvatarDraft(owner)?.spec ?? value.avatar ?? defaultAvatar);
      onUpdated(value);
    }).catch(cause => { if (alive) setError(cause instanceof Error ? cause.message : tr.genericError); });
    return () => { alive = false; };
  }, [owner, load, onUpdated]);

  useEffect(() => {
    if (!pending) return;
    const attempt = pending;
    let alive = true;
    const controller = new AbortController();
    setWorking(true);
    setError('');
    setPreview('');

    async function follow() {
      try {
        await createAvatar(attempt.id, attempt.spec, attempt.baseRevision);
        while (alive) {
          const job = await getJob(attempt.id, controller.signal);
          if (!alive) return;
          if (job.status === 'failed') {
            clearAvatarDraft(owner);
            setPending(null);
            setError(job.error || tr.genericError);
            return;
          }
          if (job.status === 'done') {
            if (!job.panels[0]?.url) throw new Error(tr.genericError);
            setPreview(job.panels[0].url);
            return;
          }
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      } catch (cause) {
        if (!alive) return;
        if (cause instanceof ApiError && [400, 404, 409, 410].includes(cause.status)) {
          clearAvatarDraft(owner);
          setPending(null);
          if (cause.status === 409) setLoad(value => value + 1);
        }
        setError(cause instanceof Error ? cause.message : tr.genericError);
      } finally {
        if (alive) setWorking(false);
      }
    }

    void follow();
    return () => { alive = false; controller.abort(); };
  }, [pending, retry, owner]);

  function closeEditor() {
    clearAvatarDraft(owner);
    clearAvatarDesign(owner);
    setPending(null);
    setPreview('');
    setWorking(false);
    setEditing(false);
    setStorageError(false);
    setError('');
  }

  async function choose(changes: Parameters<typeof updateSelfProfile>[1]) {
    if (!profile || busy) return;
    setBusy(true);
    setError('');
    try {
      const updated = await updateSelfProfile(profile.revision, changes);
      setProfile(updated);
      onUpdated(updated);
      setName(updated.displayName);
      if (changes.presetId || changes.avatarJobId || changes.clearAvatar) {
        closeEditor();
        setPreset(null);
        setConfirmRemove(false);
        setForm(updated.avatar ?? defaultAvatar);
      }
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) setLoad(value => value + 1);
      setError(cause instanceof Error ? cause.message : tr.genericError);
    } finally {
      setBusy(false);
    }
  }

  function openEditor() {
    const spec = profile?.avatar ?? defaultAvatar;
    setGroup('face');
    setForm(spec);
    setPreset(null);
    setConfirmRemove(false);
    setError('');
    setStorageError(!writeAvatarDesign(owner, spec));
    setEditing(true);
  }

  function updateField(field: keyof AvatarSpec, value: string) {
    const spec = { ...form, [field]: value };
    setForm(spec);
    setStorageError(!writeAvatarDesign(owner, spec));
  }

  function generate() {
    if (!profile || working || busy) return;
    const attempt = { id: crypto.randomUUID(), spec: form, baseRevision: profile.revision };
    if (!writeAvatarDraft(owner, attempt)) {
      setStorageError(true);
      return;
    }
    setPreview('');
    setWorking(true);
    setPending(attempt);
  }

  const disabled = busy || working || !profile;
  const matches = !!pending && Object.keys(appearanceOptions).every(key => {
    const field = key as keyof AvatarSpec;
    return pending.spec[field] === form[field];
  });
  const renderedDraft = preset ? `/avatars/${preset}.webp` : preview;

  return <section className="avatar-page view-transition">
    <header className="page-heading"><h1>{editing ? text.draft : text.heading}</h1></header>

    <div className={renderedDraft ? 'avatar-stage comparing' : 'avatar-stage'}>
      <figure className="avatar-portrait">
        {profile?.avatarUrl ? <img src={profile.avatarUrl} alt="" /> : <div className="avatar-empty"><Icon name="person" /></div>}
        <figcaption>{profile?.avatarUrl ? text.active : text.pick}</figcaption>
      </figure>
      {renderedDraft && <figure ref={previewRef} tabIndex={-1} className="avatar-portrait avatar-candidate">
        <img src={renderedDraft} alt="" />
        <figcaption>{editing && !matches ? text.oldPreview : text.preview}</figcaption>
      </figure>}
    </div>

    {error && <p className="error" role="alert">{error} {!profile && <button className="text-action" onClick={() => { setError(''); setLoad(value => value + 1); }}>{tr.app.retry}</button>}</p>}
    {storageError && <p className="error" role="status">{text.storage}</p>}

    {editing ? <div className="avatar-editor">
      <div className="avatar-groups" role="group" aria-label={text.draft}>
        {(Object.keys(groups) as Group[]).map(value =>
          <button key={value} aria-pressed={group === value} onClick={() => setGroup(value)}>{text.groups[value]}</button>
        )}
      </div>
      <div className="avatar-options">
        {groups[group].map(field => {
          if (field === 'hairColor' && form.hair === 'none') return null;
          const labels = text.options[field] as Record<string, string>;
          return <fieldset key={field}>
            <legend>{text.fields[field]}</legend>
            <div className="avatar-choices">
              {appearanceOptions[field].map(value => <button key={value} disabled={disabled} aria-pressed={form[field] === value} onClick={() => updateField(field, value)}>
                {colors[field]?.[value] && <i aria-hidden="true" style={{ backgroundColor: colors[field][value] }} />}
                {labels[value]}
              </button>)}
            </div>
          </fieldset>;
        })}
      </div>
      {working && <p className="avatar-status" role="status">{text.generating}</p>}
      <div className="avatar-actions">
        {preview && matches ? <button className="go" disabled={disabled} onClick={() => void choose({ avatarJobId: pending!.id })}>{text.use}</button>
          : pending && matches && !preview && !working
            ? <button className="go" disabled={disabled} onClick={() => setRetry(value => value + 1)}>{text.resume}</button>
            : <button className="go" disabled={disabled} onClick={generate}>{preview ? text.restart : text.generate}</button>}
        <button className="text-action" disabled={busy} onClick={closeEditor}>{text.discard}</button>
      </div>
    </div> : <>
      <div className="avatar-actions">
        {preset ? <>
          <button className="go" disabled={disabled} onClick={() => void choose({ presetId: preset })}>{text.use}</button>
          <button className="text-action" disabled={busy} onClick={() => setPreset(null)}>{text.discard}</button>
        </> : <button className="go" disabled={disabled} onClick={openEditor}>{profile?.avatar ? text.edit : text.design}</button>}
        {profile?.avatar && !preset && !confirmRemove && <button className="text-action" disabled={disabled} onClick={() => setConfirmRemove(true)}>{text.remove}</button>}
      </div>
      {confirmRemove && <div className="avatar-actions">
        <span>{text.removeConfirm}</span>
        <button className="text-action" disabled={disabled} onClick={() => void choose({ clearAvatar: true })}>{text.remove}</button>
        <button className="text-action" disabled={busy} onClick={() => setConfirmRemove(false)}>{text.discard}</button>
      </div>}
      <div className="avatar-presets" role="group" aria-label={text.presets}>
        {presetIds.map((id, index) => <button key={id} disabled={disabled} aria-pressed={(preset ?? profile?.presetId) === id}
          aria-label={text.variant(index + 1)} onClick={() => { setConfirmRemove(false); setPreset(id); }}>
          <img src={`/avatars/${id}.webp`} alt="" loading="lazy" />
        </button>)}
      </div>
      <form className="avatar-name" onSubmit={event => { event.preventDefault(); void choose({ displayName: name }); }}>
        <label>{text.name}<input maxLength={40} value={name} disabled={disabled} onChange={event => setName(event.target.value)} /></label>
        <button className="text-action" disabled={disabled || name === profile?.displayName}>{text.saveName}</button>
      </form>
      <a className="avatar-about" href="/?onboarding">{tr.intro.replay}</a>
      <AccountData owner={owner} />
    </>}
  </section>;
}
