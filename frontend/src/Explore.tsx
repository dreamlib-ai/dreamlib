import { useEffect, useState } from 'react';
import { listDreams, type Dream } from './api';
import { tr } from './strings';

type Actions = { onTell: (prompt?: string) => void; onLibrary: () => void };
export default function Explore(props: Actions) {
  const [dreams, setDreams] = useState<Dream[] | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    let alive = true;
    listDreams().then(data => { if (alive) setDreams(data); }).catch(() => { if (alive) setUnavailable(true); });
    return () => { alive = false; };
  }, []);
  return <ExploreContent {...props} dreams={dreams} unavailable={unavailable} />;
}
export function ExploreContent({ dreams, unavailable = false, onTell, onLibrary }: Actions & { dreams: Dream[] | null; unavailable?: boolean }) {
  return <div className="explore-view view-transition">
    <section className="discovery-intro"><h1>{tr.app.heroTitle}</h1><button className="go" onClick={() => onTell()}>{tr.app.heroAction}</button></section>
    {!unavailable && dreams && dreams.length > 0 && <section className="recent-journal"><h2>{tr.app.recent}</h2>{dreams.slice(0, 3).map(dream => <button key={dream.id} className="journal-entry" onClick={onLibrary}><span>{dream.title}</span><time dateTime={dream.createdAt}>{new Date(dream.createdAt).toLocaleDateString('tr-TR', { day:'numeric', month:'long' })}</time></button>)}</section>}
  </div>;
}
