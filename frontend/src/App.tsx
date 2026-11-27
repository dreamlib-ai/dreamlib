import { useCallback, useEffect, useState } from 'react';
import { getSelfProfile, type AvatarProfile, type Dream, type InterpretationType } from './api';
import AvatarPage from './AvatarPage';
import { clearAvatarDraft } from './avatar';
import Brain from './Brain';
import Library from './Library';
import Onboarding from './Onboarding';
import { SharedMagazinePage } from './Magazine';
import type { Profile } from './profile';
import { authMessage, initializeSession, saveProfile, signOut, watchAccount, type Account } from './session';
import { tr } from './strings';
import Tell from './Tell';
import Icon, { type IconName } from './Icon';

/** The koala as a line icon, drawn like the other tab icons, until the real logo. */
function Mark() {
  return <Icon name="koala" />;
}
import { clearDraft, readDraft } from './draft';
import { sessionEvent } from './telemetry';

type View = 'tell' | 'library' | 'brain' | 'profile';

/** One floating glass bar on top, on every screen size: wordmark, the three places, the profile. */
export function Nav({ view, onView, avatarUrl, onBack }: { view: View; onView: (view: View) => void; avatarUrl?:string; onBack?: (() => void) | null }) {
  const [avatarFailed,setAvatarFailed]=useState(false);
  useEffect(()=>setAvatarFailed(false),[avatarUrl]);
  const items: { view: View; label: string; icon: IconName }[] = [
    { view: 'library', label: tr.cards.library.title, icon: 'book' },
    { view: 'brain', label: tr.brain.nav, icon: 'brain' },
  ];
  return <header className="topbar"><div className="glass">
    {onBack && <button className="tab topbar-back" onClick={onBack} aria-label={tr.app.edit} title={tr.app.edit}><Icon name="chevron" /></button>}
    <button className={view === 'tell' ? 'mark on' : 'mark'} onClick={() => onView('tell')} aria-label={`${tr.brand} · ${tr.app.tell}`} aria-current={view === 'tell' ? 'page' : undefined}><Mark /></button>
    <nav className="tabs" aria-label={tr.nav.label}>
      {items.map((item) => <button key={item.view} className={view === item.view ? 'tab on' : 'tab'} aria-label={item.label} title={item.label} aria-current={view === item.view ? 'page' : undefined} onClick={() => onView(item.view)}><Icon name={item.icon} /></button>)}
    </nav>
    <button className={view === 'profile' ? 'me on' : 'me'} onClick={()=>onView('profile')} aria-label={tr.avatar.profile} aria-current={view==='profile'?'page':undefined}>{avatarUrl&&!avatarFailed?<img src={avatarUrl} alt="" onError={()=>setAvatarFailed(true)} />:<Icon name="person" />}</button>
  </div></header>;
}

export function Workspace({ account, onSignOut, start = 'tell' }: { account: Account; onSignOut: () => void; start?: View }) {
  useEffect(() => { sessionEvent(account.id); }, [account.id]);
  const [view, setView] = useState<View>(start);
  const [recentDream, setRecentDream] = useState<Dream | null>(null);
  const [draft, setDraft] = useState(0);
  const [type, setType] = useState<InterpretationType>('universal');
  const [selfProfile,setSelfProfile]=useState<AvatarProfile|null>(null);
  const [back, setBackState] = useState<(() => void) | null>(null);
  const setBack = useCallback((next: (() => void) | null) => setBackState(() => next), []);
  function openLibrary(dream?: Dream) {
    setRecentDream(dream ?? null);
    setView('library');
    window.scrollTo(0, 0);
  }
  useEffect(()=>{let alive=true;getSelfProfile().then(profile=>{if(alive)setSelfProfile(profile);}).catch(()=>{});return()=>{alive=false;};},[account.id]);
  return <div className="app-shell">
    <Nav view={view} onView={next => { if (next !== view) setRecentDream(null); setView(next); }} avatarUrl={selfProfile?.avatarUrl} onBack={view === 'tell' ? back : null} />
    <main className="page">
      {view==='profile'&&<div className="account-row"><span title={account.email}>{account.email}</span><button className="text-action" onClick={onSignOut}><Icon name="logout" />{tr.auth.signOut}</button></div>}
      <div hidden={view !== 'tell'}><Tell key={draft} owner={account.id} active={view === 'tell'} type={type} visibility={account.profile.visibility} onType={setType} onLibrary={openLibrary} onBack={setBack} /></div>
      {view === 'brain' && <Brain onTell={() => { clearDraft(account.id); setDraft(current => current + 1); setView('tell'); }} />}
      {view==='profile'&&<AvatarPage owner={account.id} onUpdated={setSelfProfile} />}
      {view === 'library' && <div className="library-view"><Library initialDream={recentDream} onRemoved={(id) => {
        if (readDraft(account.id)?.id === id) { clearDraft(account.id); setDraft(current => current + 1); }
      }} onTell={() => { clearDraft(account.id); setDraft(current => current + 1); setView('tell'); }} /></div>}
    </main>
  </div>;
}

const SHARED = /^\/m\/([A-Za-z0-9_-]{8,32})\/?$/;

/** G6: a shared magazine opens without an account; everything else is the signed-in app. */
export default function App() {
  const slug = window.location.pathname.match(SHARED)?.[1];
  return slug ? <SharedMagazinePage slug={slug} /> : <AccountApp />;
}

function AccountApp() {
  const [account, setAccount] = useState<Account | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [replay, setReplay] = useState(() => new URLSearchParams(window.location.search).has('onboarding'));

  useEffect(() => {
    let alive = true;
    let initialized = false;
    const stop = watchAccount((next) => { if (alive && initialized) setAccount(next); });
    initializeSession().then((next) => { if (alive) setAccount(next); })
      .catch((cause) => { if (alive) setError(authMessage(cause)); })
      .finally(() => { initialized = true; if (alive) setReady(true); });
    return () => { alive = false; stop(); };
  }, []);

  async function finish(profile: Profile) {
    const updated = await saveProfile(profile);
    setAccount(updated); setReplay(false);
    const location = new URL(window.location.href);
    location.searchParams.delete('onboarding');
    window.history.replaceState(null, '', location.pathname + location.search);
  }

  async function leave() {
    try { await signOut(); if (account) { clearDraft(account.id); clearAvatarDraft(account.id); } setAccount(null); setError(''); }
    catch (cause) { setError(authMessage(cause)); }
  }

  if (!ready) return <main className="session-loading" role="status"><span>{tr.brand}</span><p>{tr.auth.loading}</p></main>;
  if (!account || !account.profile.onboarded || replay) return <Onboarding account={account} replay={replay} initialError={error} onDone={finish} />;
  return <><Workspace key={account.id} account={account} onSignOut={() => void leave()} />{error && <p className="session-error" role="alert">{error}</p>}</>;
}
