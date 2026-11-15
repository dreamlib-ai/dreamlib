import { useEffect, useState } from 'react';
import { checkGoogleProvider } from './api';
import Mascot, { type Pose } from './Mascot';
import Icon from './Icon';
import Worn from './Worn';
import { defaultProfile, typicalThemes, type Profile, type TypicalTheme, type Visibility } from './profile';
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

/** F5: optional; nothing chosen is a fine answer. */
function Themes({ value, onToggle, disabled }: { value: TypicalTheme[]; onToggle: (key: TypicalTheme) => void; disabled: boolean }) {
  return <div className="theme-picks" role="group" aria-label={text.themesTitle}>
    {typicalThemes.map(key => <button key={key} disabled={disabled} aria-pressed={value.includes(key)} className={value.includes(key) ? 'choice selected' : 'choice'}
      onClick={() => onToggle(key)}>{text.themes[key]}</button>)}
  </div>;
}

/** Duolingo-like steps: one thing per screen, a progress bar on top, one big button at the bottom,
 * and the koala in a pose that fits the step. Signed-out visitors start at hello; after Google they land on privacy. */
const STEPS = ['hello', 'how', 'signin', 'privacy', 'themes'] as const;
type Step = typeof STEPS[number];
const POSE: Record<Step, Pose> = { hello: 'wave', how: 'listen', signin: 'hold', privacy: 'curious', themes: 'think' };

export default function Onboarding({ account, replay, initialError, onDone }: {
  account: Account | null; replay: boolean; initialError: string; onDone: (profile: Profile) => Promise<void>;
}) {
  const [step, setStep] = useState<Step>(account && !replay ? 'privacy' : 'hello');
  const [seen, setSeen] = useState<TypicalTheme[]>(account?.profile.seenThemes ?? []);
  const [visibility, setVisibility] = useState<Visibility>(account?.profile.visibility ?? defaultProfile.visibility);
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (account) {
      setVisibility(account.profile.visibility);
      setSeen(account.profile.seenThemes ?? []);
      if (!replay) setStep('privacy');
    }
  }, [account?.id, replay]);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError('');
    try { await action(); } catch (cause) { setError(authMessage(cause)); } finally { setBusy(false); }
  }
  const index = STEPS.indexOf(step);
  const first = index === 0 || (step === 'privacy' && !!account && !replay);
  function forward() {
    if (step === 'signin' && !account) { void run(async () => { await checkGoogleProvider(); await signInGoogle(); }); return; }
    if (step === 'themes') { void run(() => onDone({ onboarded: true, visibility, ...(seen.length ? { seenThemes: seen } : {}) })); return; }
    setError(''); setStep(STEPS[index + 1]);
  }
  const copy = step === 'hello' ? text.hello : step === 'how' ? text.how : step === 'signin' ? text.signin
    : step === 'privacy' ? { title: text.privacyTitle, body: text.privacyText } : { title: text.themesTitle, body: text.themesText };
  const action = busy ? (step === 'signin' ? text.redirecting : tr.saving) : step === 'hello' ? text.hello.action
    : step === 'signin' && !account ? text.google : step === 'themes' ? text.start : text.next;

  return <main className={`steps steps-${step}`}>
    <header className="steps-top">
      <button className="steps-back" disabled={busy || first} onClick={() => { setError(''); setStep(STEPS[index - 1]); }} aria-label={tr.back}><Icon name="chevron" /></button>
      <ol className="steps-clouds" role="progressbar" aria-label={text.progress(index + 1, STEPS.length)} aria-valuemin={1} aria-valuemax={STEPS.length} aria-valuenow={index + 1}>
        {STEPS.map((key, k) => <li key={key} className={k < index ? 'done' : k === index ? 'now' : ''}><svg viewBox="0 0 40 26" aria-hidden="true"><path d="M11 25a8 8 0 0 1-1.2-15.9A10 10 0 0 1 29 7.6 7.8 7.8 0 0 1 31 25Z" /></svg></li>)}
      </ol>
    </header>
    <div key={step} className="steps-body" aria-busy={busy}>
      <Mascot pose={POSE[step]} className="steps-koala" />
      <h1><Worn text={copy.title} /></h1>
      <p className="steps-text">{copy.body}</p>
      {step === 'privacy' && <Privacy value={visibility} onChange={setVisibility} disabled={busy} />}
      {step === 'themes' && <Themes value={seen} onToggle={key => setSeen(now => now.includes(key) ? now.filter(k => k !== key) : [...now, key])} disabled={busy} />}
    </div>
    <footer className="steps-foot">
      {error && <p className="error auth-error" role="alert">{error}</p>}
      <button className="cta cloud-button" disabled={busy} onClick={forward}><span className="cloud-fill" aria-hidden="true"><i /><i /></span><span className="cta-label">{step === 'signin' && !account && <GoogleMark />}{action}</span></button>
      {step === 'hello' && <nav className="steps-info" aria-label="Uygulama bilgileri"><a href="/about.html">Dreamlib hakkında</a><a href="/privacy.html">Gizlilik</a></nav>}
    </footer>
  </main>;
}
