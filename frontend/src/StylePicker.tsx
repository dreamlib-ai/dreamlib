import { useEffect, useId, useRef, useState } from 'react';
import type { ArtStyle, AvatarProfile } from './api';
import { artStyles } from './draft';
import Icon from './Icon';
import { tr } from './strings';
import './style-picker.css';

const origin = (import.meta.env.VITE_SUPABASE_URL ?? '').replace(/\/$/, '');
const previews = `${origin}/storage/v1/object/public/glyphs/style-previews/v1`;
const text = tr.stylePicker;

export default function StylePicker({ initial, remembered, profile, onClose, onStart }: {
  initial: ArtStyle;
  remembered: boolean;
  profile: AvatarProfile | null;
  onClose: () => void;
  onStart: (style: ArtStyle, remember: boolean, avatarRevision?: number) => void;
}) {
  const [style, setStyle] = useState(initial);
  const [remember, setRemember] = useState(remembered);
  const [avatar, setAvatar] = useState(false);
  const heading = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const avatarAvailable = Boolean(profile?.avatar && profile.avatarUrl);

  useEffect(() => {
    const node = dialog.current;
    node?.showModal();
    node?.querySelector<HTMLInputElement>('input[type="radio"]:checked')?.focus({ preventScroll: true });
    return () => node?.close();
  }, []);

  function dismiss() {
    dialog.current?.close();
    onClose();
  }

  return <dialog className="dream-style-picker" aria-labelledby={heading} ref={dialog}
    onCancel={event => { event.preventDefault(); dismiss(); }}>
    <form onSubmit={event => { event.preventDefault(); onStart(style, remember, avatar && avatarAvailable ? profile?.revision : undefined); }}>
      <header>
        <button className="style-picker-back" type="button" aria-label={tr.back} onClick={dismiss}><Icon name="chevron" /></button>
        <h2 id={heading}>{text.title}</h2>
      </header>
      <fieldset className="style-picks" aria-labelledby={heading}>
        {artStyles.map(value => <label key={value}>
          <input type="radio" name="dream-style" value={value} checked={style === value} onChange={() => setStyle(value)} />
          <span className="style-option">
            <img src={`${previews}/${value}.webp`} alt="" width={480} height={320} />
            <span>{tr.styles[value]}</span>
          </span>
        </label>)}
      </fieldset>
      <div className="style-prefs">
        {avatarAvailable && <label>
          <input type="checkbox" checked={avatar} onChange={event => setAvatar(event.target.checked)} />
          <img src={profile!.avatarUrl} alt="" width={28} height={28} />
          <span>{text.avatar}</span>
        </label>}
        <label>
          <input type="checkbox" checked={remember} onChange={event => setRemember(event.target.checked)} />
          <span>{text.remember}</span>
        </label>
      </div>
      <footer className="style-picker-footer"><button className="style-start" type="submit">{text.start}</button></footer>
    </form>
  </dialog>;
}
