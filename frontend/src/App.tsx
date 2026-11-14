import { useEffect, useState } from 'react';
import { getSelfProfile, type AvatarProfile, type InterpretationType } from './api';
import AvatarPage from './AvatarPage';
import { clearAvatarDraft } from './avatar';
import Brain from './Brain';
import Library from './Library';
import Onboarding from './Onboarding';
import type { Profile } from './profile';
import { authMessage, initializeSession, saveProfile, signOut, watchAccount, type Account } from './session';
import { tr } from './strings';
import Tell from './Tell';
import Icon, { type IconName } from './Icon';
import { clearDraft, readDraft } from './draft';
import { sessionEvent } from './telemetry';

type View = 'tell' | 'library' | 'brain' | 'profile';

export function Nav({ account, view, onView, onSignOut, avatarUrl }: { account: Account; view: View; onView: (view: View) => void; onSignOut: () => void; avatarUrl?:string }) {
  const [avatarFailed,setAvatarFailed]=useState(false);
  useEffect(()=>setAvatarFailed(false),[avatarUrl]);
  const items: { view: View; label: string; icon: IconName }[] = [
    { view: 'tell', label: tr.app.tell, icon: 'mic' },
    { view: 'library', label: tr.cards.library.title, icon: 'book' },
    { view: 'brain', label: tr.brain.nav, icon: 'spark' },
  ];
  return <header className="nav"><div className="nav-in">
    <button className="brand" onClick={() => onView('tell')}><span>{tr.brand}</span></button>
    <nav className="links" data-view={view} aria-label={tr.nav.label}><span className="nav-selection" aria-hidden="true" />
      {items.map((item) => <button key={item.view} className={view === item.view ? 'link on' : 'link'} aria-current={view === item.view ? 'page' : undefined} onClick={() => onView(item.view)}><Icon name={item.icon} /><span>{item.label}</span></button>)}
    </nav>
    <div className="account"><button className="profile-open" onClick={()=>onView('profile')} aria-label={tr.avatar.profile} aria-current={view==='profile'?'page':undefined}>{avatarUrl&&!avatarFailed?<span className="profile-portrait"><img src={avatarUrl} alt="" onError={()=>setAvatarFailed(true)} /></span>:<Icon name="person" />}</button><span title={account.email}>{account.email}</span><button className="sign-out" onClick={onSignOut} aria-label={tr.auth.signOut}><Icon name="logout" /></button></div>
  </div></header>;
}

export function Workspace({ account, onSignOut }: { account: Account; onSignOut: () => void }) {
  useEffect(() => { sessionEvent(account.id); }, [account.id]);
  const [view, setView] = useState<View>('tell');
  const [draft, setDraft] = useState(0);
  const [type, setType] = useState<InterpretationType>('universal');
  const [selfProfile,setSelfProfile]=useState<AvatarProfile|null>(null);
  useEffect(()=>{let alive=true;getSelfProfile().then(profile=>{if(alive)setSelfProfile(profile);}).catch(()=>{});return()=>{alive=false;};},[account.id]);
  return <div className="app-shell">
    <Nav account={account} view={view} onView={setView} onSignOut={onSignOut} avatarUrl={selfProfile?.avatarUrl} />
    <main className="page">
      <div hidden={view !== 'tell'}><Tell key={draft} owner={account.id} active={view === 'tell'} type={type} visibility={account.profile.visibility} onType={setType} onLibrary={() => setView('library')} onProfile={()=>setView('profile')} /></div>
      {view === 'brain' && <Brain onTell={() => { clearDraft(account.id); setDraft(current => current + 1); setView('tell'); }} />}
      {view==='profile'&&<AvatarPage owner={account.id} onUpdated={setSelfProfile} />}
      {view === 'library' && <div className="library-view"><Library onRemoved={(id) => {
        if (readDraft(account.id)?.id === id) { clearDraft(account.id); setDraft(current => current + 1); }
      }} onTell={() => { clearDraft(account.id); setDraft(current => current + 1); setView('tell'); }} /></div>}
    </main>
  </div>;
}

export default function App() {
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
