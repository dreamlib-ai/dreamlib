import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { deleteDream, listDreamPage, type Dream, type Panel } from './api';
import { decodeBlurhash } from './blurhash';
import { placeCards, wallColumns } from './wall';
import Result from './Result';
import Icon from './Icon';
import Mascot from './Mascot';
import JournalEditor from './JournalEditor';
import { tr } from './strings';
import { normalizeTag, recurringThemes } from './themes';
import { effectiveFeatures } from './features';
import type { Genre } from './api';

const text = tr.library;
const day = (iso: string) => new Date(iso).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });

function Detail({ dream, onBack, onRemoved, onUpdated }: { dream: Dream; onBack: () => void; onRemoved: () => void; onUpdated: (dream: Dream) => void }) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');

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
  const [filter, setFilter] = useState<'all' | 'books' | 'text' | 'favorites'>('all');
  const [from, setFrom] = useState('');
  const [until, setUntil] = useState('');
  const [genre, setGenre] = useState('');
  const [emotion, setEmotion] = useState('');
  const themes = recurringThemes((dreams ?? []).map(dream => ({ ...dream, tags:effectiveFeatures(dream).tags })));
  const availableGenres = [...new Set((dreams ?? []).flatMap(dream => effectiveFeatures(dream).genres))];
  const availableEmotions = [...new Map((dreams ?? []).flatMap(dream => dream.emotions.filter(e => e.pct > 0).map(e => [normalizeTag(e.label),e.label] as const))).entries()];
  const [themeFilter, setThemeFilter] = useState<string | null>(null);
  const recentIds = new Set(dreams?.slice(0, 15).map(dream => dream.id));
  useEffect(() => {
    if (themeFilter && !recurringThemes((dreams ?? []).map(d => ({...d,tags:effectiveFeatures(d).tags}))).some(theme => theme.label === themeFilter)) setThemeFilter(null);
  }, [dreams, themeFilter]);
  const narrowed = Boolean(query || themeFilter || filter !== 'all' || from || until || genre || emotion);
  useEffect(() => {
    if (narrowed && hasMore && !loadingMore) onMore?.();  // a search must see every dream, not only the pages read so far
  }, [narrowed, hasMore, loadingMore, onMore]);
  const filtered = dreams?.filter((dream) => {
    const effective = effectiveFeatures(dream);
    const matches = `${dream.title} ${dream.originalText} ${effective.tags.join(' ')}`.toLocaleLowerCase('tr-TR').includes(query.toLocaleLowerCase('tr-TR'));
    const matchesTheme = !themeFilter || (recentIds.has(dream.id) && effective.tags.some(tag => normalizeTag(tag) === themeFilter));
    const date = dream.journal?.dreamedOn ?? dream.createdAt.slice(0, 10);
    return matches && matchesTheme && (!genre || effective.genres.includes(genre as Genre)) && (!emotion || dream.emotions.some(e => normalizeTag(e.label) === emotion && e.pct > 0)) && (!from || date >= from) && (!until || date <= until) && (filter === 'all' || (filter === 'favorites' ? dream.journal?.favorite : filter === 'books' ? dream.panels.length > 0 : dream.panels.length === 0));
  });
  return <div className="library-content view-transition">
    <header className="page-heading"><h1>{text.heading}</h1>{dreams && dreams.length > 0 && <button className="new-dream" onClick={onTell} aria-label={tr.app.newDream}><Icon name="plus" /></button>}</header>
    {themes.length > 0 && <section className="recurring-themes" aria-label={tr.personal.themes}><h2>{tr.personal.themes}</h2><div>
      {themes.map(theme => <button key={theme.label} aria-pressed={themeFilter === theme.label} onClick={() => { setThemeFilter(themeFilter === theme.label ? null : theme.label); setQuery(''); setFilter('all'); }}><span>{theme.label}</span><small>{tr.personal.count(theme.count)}</small></button>)}
    </div></section>}
    {dreams && dreams.length > 0 && <div className="library-tools"><label className="library-search"><Icon name="search" /><input type="search" aria-label={tr.app.search} placeholder={tr.app.search} value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <div className="library-filters" role="group" aria-label={text.heading}>{(['all', 'books', 'text', 'favorites'] as const).map((key) => <button key={key} aria-pressed={filter === key} className={filter === key ? 'choice selected' : 'choice'} onClick={() => setFilter(key)}>{key === 'all' ? tr.app.filterAll : key === 'books' ? tr.app.filterBooks : key === 'favorites' ? tr.journal.favorites : tr.app.filterText}</button>)}</div>
      <details className="library-dates"><summary>{tr.classification.filters}</summary><div>
        <label>{tr.journal.from}<input type="date" value={from} max={until || undefined} onInput={e => setFrom(e.currentTarget.value)} /></label><label>{tr.journal.until}<input type="date" value={until} min={from || undefined} onInput={e => setUntil(e.currentTarget.value)} /></label>
        {availableGenres.length > 0 && <label>{tr.classification.genres}<select value={genre} onChange={e => setGenre(e.target.value)}><option value="">{tr.classification.all}</option>{availableGenres.map(key => <option key={key} value={key}>{tr.classification.genreLabels[key]}</option>)}</select></label>}
        {availableEmotions.length > 0 && <label>{tr.classification.emotion}<select value={emotion} onChange={e => setEmotion(e.target.value)}><option value="">{tr.classification.all}</option>{availableEmotions.map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>}
        <button className="text-action" onClick={() => { setFrom(''); setUntil(''); setGenre(''); setEmotion(''); }}>{tr.journal.clear}</button></div></details>
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
    {!error && dreams === null && <p className="small" role="status">{text.loading}</p>}
    {dreams?.length === 0 && <EmptyLibrary onTell={onTell} />}
    {dreams && dreams.length > 0 && filtered?.length === 0 && <p className="no-results">{tr.app.noResults}</p>}
    {filtered && filtered.length > 0 && <DreamWall dreams={filtered} onOpen={onOpen} />}
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

const placeholders = new Map<string, string>();
/** A 32×32 picture of the BlurHash, drawn once per hash. */
function placeholder(hash: string): string {
  if (!hash) return '';
  const known = placeholders.get(hash);
  if (known !== undefined) return known;
  let url = '';
  const pixels = decodeBlurhash(hash, 32, 32);
  const canvas = pixels ? document.createElement('canvas') : null;
  const ctx = canvas?.getContext('2d');
  if (pixels && canvas && ctx) {
    canvas.width = canvas.height = 32;
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels), 32, 32), 0, 0);
    url = canvas.toDataURL();
  }
  placeholders.set(hash, url);
  return url;
}

function Cover({ panel }: { panel: Panel }) {
  const [shown, setShown] = useState(false);
  const hash = placeholder(panel.blurhash ?? '');
  const ratio = panel.width && panel.height ? `${panel.width} / ${panel.height}` : '1 / 1';
  return <span className="wall-cover" style={{ aspectRatio: ratio, backgroundColor: panel.color || undefined, backgroundImage: hash ? `url(${hash})` : undefined }}>
    <img src={panel.thumb || panel.url} alt="" loading="lazy" decoding="async" className={shown ? 'shown' : ''} onLoad={() => setShown(true)} />
  </span>;
}

/** Masonry: each card goes under the shortest column; the page keeps them in date order for keyboards and screen readers. */
function DreamWall({ dreams, onOpen }: { dreams: Dream[]; onOpen: (dream: Dream) => void }) {
  const box = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const place = () => {
      const { count, gap } = wallColumns(el.clientWidth);
      const width = (el.clientWidth - gap * (count - 1)) / count;
      const cards = [...el.children] as HTMLElement[];
      for (const card of cards) card.style.width = `${width}px`;
      const { spots, height } = placeCards(cards.map((card) => card.offsetHeight), count, width, gap);
      cards.forEach((card, i) => { card.style.transform = `translate(${spots[i].x}px, ${spots[i].y}px)`; });
      el.style.height = `${height}px`;
    };
    place();
    if (typeof ResizeObserver === 'undefined') return;
    const watch = new ResizeObserver(place);
    watch.observe(el);
    for (const card of el.children) watch.observe(card);
    return () => watch.disconnect();
  }, [dreams]);
  return <div ref={box} className="wall">{dreams.map((dream) => {
    const panel = dream.panels.find((p) => p.url);
    return <button key={dream.id} className={panel ? 'wall-card' : 'wall-card text-only'} onClick={() => onOpen(dream)}>
      {panel && <Cover panel={panel} />}
      <span className="wall-info"><small>{day(dream.journal?.dreamedOn ? dream.journal.dreamedOn + 'T12:00:00' : dream.createdAt)}{dream.journal?.favorite && <Icon name="heart" />}</small><b>{dream.title}</b>{!panel && <span className="wall-excerpt">{dream.originalText.slice(0, 220)}</span>}</span>
    </button>;
  })}</div>;
}

export function EmptyLibrary({ onTell }: { onTell: () => void }) {
  return <section className="library-empty"><Mascot theme="sleep" className="sleeping-koala" /><div className="empty-copy"><h2>{text.empty}</h2><button className="go" onClick={onTell}>{text.emptyAction}</button></div></section>;
}
