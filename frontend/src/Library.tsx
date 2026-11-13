import { useEffect, useState } from 'react';
import { deleteDream, listDreams, type Dream } from './api';
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
  const [error, setError] = useState('');
  const [open, setOpen] = useState<Dream | null>(null);

  useEffect(() => {
    let alive = true;
    listDreams()
      .then((d) => alive && setDreams(d))
      .catch((e) => alive && setError(e instanceof Error ? e.message : tr.genericError));
    return () => {
      alive = false;
    };
  }, []);

  const opened = open;
  return <>
    <div hidden={opened !== null}><LibraryShelf dreams={dreams} error={error} onTell={onTell} onOpen={setOpen} /></div>
    {opened && <Detail dream={opened} onBack={() => setOpen(null)} onUpdated={updated => { setOpen(updated); setDreams(list => (list ?? []).map(d => d.id === updated.id ? updated : d)); }} onRemoved={() => {
      onRemoved?.(opened.id);
      setDreams((list) => (list ?? []).filter((dream) => dream.id !== opened.id));
      setOpen(null);
    }} />}
  </>;
}

export function LibraryShelf({ dreams, error = '', onTell, onOpen }: { dreams: Dream[] | null; error?: string; onTell: () => void; onOpen: (dream: Dream) => void }) {
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
    <div className="dreams">{filtered?.map((dream) => <button key={dream.id} className="dream" onClick={() => onOpen(dream)}>
      {dream.panels[0]?.url && <span className="cover"><img src={dream.panels[0].url} alt="" loading="lazy" /></span>}
      <span className="dream-info"><small>{day(dream.journal?.dreamedOn ? dream.journal.dreamedOn + 'T12:00:00' : dream.createdAt)}{dream.journal?.favorite && <Icon name="heart" />}</small><b>{dream.title}</b><span className="dream-excerpt">{dream.originalText.slice(0, 180)}</span></span>    </button>)}</div>
  </div>;
}

export function EmptyLibrary({ onTell }: { onTell: () => void }) {
  return <section className="library-empty"><Mascot theme="sleep" className="sleeping-koala" /><div className="empty-copy"><h2>{text.empty}</h2><button className="go" onClick={onTell}>{text.emptyAction}</button></div></section>;
}
