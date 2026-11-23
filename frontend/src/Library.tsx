import { useEffect, useRef, useState } from 'react';
import { deleteDream, listDreamPage, type Dream } from './api';
import Magazine, { Anniversary, ShareMagazine, useMagazine } from './Magazine';
import Result from './Result';
import DreamShelf from './DreamShelf';
import Icon from './Icon';
import Mascot from './Mascot';
import JournalEditor from './JournalEditor';
import { tr } from './strings';

const text = tr.library;
const day = (iso: string) => new Date(iso).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });

function Detail({ dream, onBack, onRemoved, onUpdated }: { dream: Dream; onBack: () => void; onRemoved: () => void; onUpdated: (dream: Dream) => void }) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');
  const [magazine, setMagazine] = useMagazine(dream.id, dream.panels.length > 0);
  const [reading, setReading] = useState(false);

  async function remove() {
    try {
      await deleteDream(dream.id);
      onRemoved();
    } catch (e) {
      setError(e instanceof Error ? e.message : tr.genericError);
    }
  }

  return (
    <div className="detail">
      <button className="back" onClick={onBack} aria-label={tr.back}>
        <Icon name="chevron" />
      </button>
      <p className="small when">{dream.journal?.dreamedOn ? `${tr.journal.date}: ${day(dream.journal.dreamedOn + 'T12:00:00')}` : `${tr.journal.recorded}: ${day(dream.createdAt)}`}</p>
      <Result analysis={dream}>
        <details className="original-dream"><summary>{tr.app.original}</summary><p>{dream.originalText}</p></details>
        <JournalEditor dream={dream} onUpdated={onUpdated} />
        {magazine && <button className="go read-magazine" onClick={() => setReading(true)}><Icon name="book" />{tr.magazine.open}</button>}
        {reading && magazine && <Magazine magazine={magazine} onClose={() => setReading(false)} />}
        {magazine && <ShareMagazine magazine={magazine} onChange={setMagazine} />}
        {dream.panels.length > 0 && (
          <div className="shots">
            {dream.panels.map((p) => (
              <figure key={p.path}>
                <img src={p.url} alt={p.caption} />
                {p.caption && <figcaption>{p.caption}</figcaption>}
              </figure>
            ))}
          </div>
        )}
        <div className="remove">
          {confirming ? (
            <>
              <span>{text.removeSure}</span>
              <button className="go tiny" onClick={remove}>
                {text.removeYes}
              </button>
              <button className="go tiny quiet" onClick={() => setConfirming(false)}>
                {text.cancel}
              </button>
            </>
          ) : (
            <button className="go tiny quiet" onClick={() => setConfirming(true)}>
              {text.remove}
            </button>
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </Result>
    </div>
  );
}

export default function Library({ onTell, onRemoved }: { onTell: () => void; onRemoved?: (id: string) => void }) {
  const [dreams, setDreams] = useState<Dream[] | null>(null);
  const [next, setNext] = useState<string | undefined>();
  const [error, setError] = useState('');
  const [moreFailed, setMoreFailed] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const busy = useRef(false);
  const [open, setOpen] = useState<Dream | null>(null);

  useEffect(() => {
    let alive = true;
    listDreamPage()
      .then((page) => { if (alive) { setDreams(page.dreams); setNext(page.next); } })
      .catch((e) => alive && setError(e instanceof Error ? e.message : tr.genericError));
    return () => {
      alive = false;
    };
  }, []);

  function more() {
    if (!next || busy.current) return;
    busy.current = true;
    setLoadingMore(true);
    setMoreFailed(false);
    listDreamPage(next)
      .then((page) => {
        setDreams((list) => {
          const known = new Set((list ?? []).map((d) => d.id));
          return [...(list ?? []), ...page.dreams.filter((d) => !known.has(d.id))];
        });
        setNext(page.next);
      })
      .catch(() => setMoreFailed(true))
      .finally(() => { busy.current = false; setLoadingMore(false); });
  }

  const opened = open;
  return <>
    <div hidden={opened !== null}><LibraryShelf dreams={dreams} error={error} onTell={onTell} onOpen={setOpen} hasMore={Boolean(next) && !moreFailed} loadingMore={loadingMore} moreFailed={moreFailed} onMore={more} /></div>
    {opened && <Detail dream={opened} onBack={() => setOpen(null)} onUpdated={updated => { setOpen(updated); setDreams(list => (list ?? []).map(d => d.id === updated.id ? updated : d)); }} onRemoved={() => {
      onRemoved?.(opened.id);
      setDreams((list) => (list ?? []).filter((dream) => dream.id !== opened.id));
      setOpen(null);
    }} />}
  </>;
}

type Paging = { hasMore?: boolean; loadingMore?: boolean; moreFailed?: boolean; onMore?: () => void };

export function LibraryShelf({ dreams, error = '', onTell, onOpen, hasMore = false, loadingMore = false, moreFailed = false, onMore }: { dreams: Dream[] | null; error?: string; onTell: () => void; onOpen: (dream: Dream) => void } & Paging) {
  const [query, setQuery] = useState('');
  useEffect(() => {
    if (query && hasMore && !loadingMore) onMore?.();  // a search must see every dream, not only the pages read so far
  }, [query, hasMore, loadingMore, onMore]);
  const needle = query.trim().toLocaleLowerCase('tr-TR');
  const filtered = dreams?.filter((dream) => !needle || `${dream.title} ${dream.originalText}`.toLocaleLowerCase('tr-TR').includes(needle));
  return <div className="library-content view-transition">
    <header className="page-heading"><h1>{text.heading}</h1></header>
    {dreams && dreams.length > 0 && <div className="library-tools">
      <label className="library-search"><Icon name="search" /><input type="search" aria-label={tr.app.search} placeholder={tr.app.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <button className="new-dream" onClick={onTell} aria-label={tr.app.newDream}><Icon name="plus" /></button>
    </div>}
    {dreams && dreams.length > 0 && <Anniversary />}
    {error && <p className="error" role="alert">{error}</p>}
    {!error && dreams === null && <p className="small" role="status">{text.loading}</p>}
    {dreams?.length === 0 && <EmptyLibrary onTell={onTell} />}
    {dreams && dreams.length > 0 && filtered?.length === 0 && <p className="no-results">{tr.app.noResults}</p>}
    {filtered && filtered.length > 0 && <DreamShelf dreams={filtered} onOpen={onOpen} />}
    {hasMore && <MoreSentinel onMore={onMore} />}
    {loadingMore && <p className="small wall-status" role="status">{text.loading}</p>}
    {moreFailed && <p className="wall-status"><span className="error">{text.moreFailed}</span> <button className="text-action" onClick={onMore}>{text.retry}</button></p>}
  </div>;
}

/** Asks for the next page a little before the end of the wall comes into view. */
function MoreSentinel({ onMore }: { onMore?: () => void }) {
  const spot = useRef<HTMLDivElement>(null);
  const ask = useRef(onMore);
  ask.current = onMore;
  useEffect(() => {
    const el = spot.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const seen = new IntersectionObserver((entries) => { if (entries.some((e) => e.isIntersecting)) ask.current?.(); }, { rootMargin: '600px 0px' });
    seen.observe(el);
    return () => seen.disconnect();
  }, []);
  return <div ref={spot} className="wall-sentinel" aria-hidden="true" />;
}

export function EmptyLibrary({ onTell }: { onTell: () => void }) {
  return <section className="library-empty"><Mascot pose="sleep" className="sleeping-koala" /><div className="empty-copy"><h2>{text.empty}</h2><button className="go" onClick={onTell}>{text.emptyAction}</button></div></section>;
}
