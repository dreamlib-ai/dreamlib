import { useEffect, useState } from 'react';
import { checkGoogleProvider } from './api';
import Mascot from './Mascot';
import Icon from './Icon';
import DreamIntro from './DreamIntro';
import { defaultProfile, type Profile, type Visibility } from './profile';
import { authMessage, signInGoogle, type Account } from './session';
import { tr } from './strings';

const text = tr.onboarding;

function GoogleMark() {
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 48 48"><path fill="#4285f4" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11c-.5 2.5-1.9 4.6-4 6v5h6.5c3.8-3.5 6.1-8.7 6.1-14.7Z"/><path fill="#34a853" d="M24 44c5.4 0 9.9-1.8 13.2-4.8l-6.5-5c-1.8 1.2-4.1 1.9-6.7 1.9-5.2 0-9.6-3.5-11.2-8.2H6.1V33A20 20 0 0 0 24 44Z"/><path fill="#fbbc05" d="M12.8 27.9a12 12 0 0 1 0-7.8V15H6.1a20 20 0 0 0 0 18l6.7-5.1Z"/><path fill="#ea4335" d="M24 11.9c2.9 0 5.5 1 7.5 2.9l5.6-5.6A19 19 0 0 0 24 4 20 20 0 0 0 6.1 15l6.7 5.1C14.4 15.4 18.8 11.9 24 11.9Z"/></svg>;
}

function Privacy({ value, onChange, disabled }: { value: Visibility; onChange: (value: Visibility) => void; disabled: boolean }) {
  const options = [{ key: 'private' as const, ...text.onlyMe }, { key: 'public' as const, ...text.everyone }];
  return <div className="options" role="radiogroup" aria-label={text.privacyTitle} onKeyDown={(event) => {
    if (disabled || !['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft'].includes(event.key)) return;
    event.preventDefault();
    const selected = options.findIndex((option) => option.key === value);
    const next = (selected + 1) % options.length;
    onChange(options[next].key);
    event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="radio"]')[next]?.focus();
  }}>
    {options.map((option) => <button key={option.key} disabled={disabled} role="radio" tabIndex={value === option.key ? 0 : -1}
      aria-checked={value === option.key} className={value === option.key ? 'opt on' : 'opt'} onClick={() => onChange(option.key)}>
      <span><b>{option.label}</b><small>{option.detail}</small></span>
      <span className="choice-check" aria-hidden="true">{value === option.key && <Icon name="check" />}</span>
    </button>)}
  </div>;
}

export default function Onboarding({ account, replay, initialError, onDone }: {
  account: Account | null; replay: boolean; initialError: string; onDone: (profile: Profile) => Promise<void>;
}) {
  const [step, setStep] = useState<'welcome' | 'privacy'>(account && !replay ? 'privacy' : 'welcome');
  const [visibility, setVisibility] = useState<Visibility>(account?.profile.visibility ?? defaultProfile.visibility);
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);
  const [intro, setIntro] = useState(!account || replay);

  useEffect(() => {
    if (account) {
      setVisibility(account.profile.visibility);
      if (!replay) setStep('privacy');
    }
  }, [account?.id, replay]);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError('');
    try { await action(); } catch (cause) { setError(authMessage(cause)); } finally { setBusy(false); }
  }
  function enter() {
    if (account) { setStep('privacy'); return; }
    void run(async () => { await checkGoogleProvider(); await signInGoogle(); });
  }

  if (intro) return <DreamIntro onDone={() => setIntro(false)} />;
  return <main className={`onb onb-${step}`}>
    <aside className="onb-art" aria-hidden="true"><Mascot scene theme={step === 'privacy' ? 'curious' : 'cloud'} /></aside>
    <section className="onb-main">
      <div className="onb-top">
        {step === 'privacy' ? <button className="back" disabled={busy} onClick={() => { setStep('welcome'); setError(''); }} aria-label={tr.back}><Icon name="chevron" /></button> : <span className="onb-wordmark">{tr.brand}</span>}
      </div>
      <div key={step} className="onb-body" aria-busy={busy}>
        <h1 className="onb-title">{step === 'welcome' ? text.welcomeTitle : text.privacyTitle}</h1>
        {step === 'welcome' ? <div className="onb-actions"><button className="go" disabled={busy} onClick={enter}>
          {!account && <GoogleMark />}{busy ? text.redirecting : account ? text.continue : text.google}
        </button></div> : <>
          <p className="onb-text">{text.privacyText}</p>
          <Privacy value={visibility} onChange={setVisibility} disabled={busy} />
          <div className="onb-actions"><button className="go" disabled={busy} onClick={() => void run(() => onDone({ onboarded: true, visibility }))}>{busy ? tr.saving : text.start}</button></div>
        </>}
        {error && <p className="error auth-error" role="alert">{error}</p>}
        <nav className="onb-info" aria-label="Uygulama bilgileri"><a href="/about.html">Dreamlib hakkında</a><a href="/privacy.html">Gizlilik</a></nav>
        <button className="intro-replay" onClick={() => setIntro(true)}>{tr.intro.replay}</button>
      </div>
    </section>
  </main>;
}
