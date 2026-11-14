import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { getMagazine, type Magazine as MagazineData, type MagazinePage, type Panel } from './api';
import Icon from './Icon';
import Picture from './Picture';
import { tr } from './strings';

const text = tr.magazine;
const SWIPE = 48; // px of horizontal travel that turns a page
const day = (iso: string) => iso ? new Date(iso + 'T12:00:00').toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' }) : '';

/** The dream's magazine if the `magazine` job has laid it out; null while there is none (G4 answers 404). */
export function useMagazine(dreamId: string, hasPanels: boolean) {
  const [magazine, setMagazine] = useState<MagazineData | null>(null);
  useEffect(() => {
    setMagazine(null);
    if (!hasPanels) return;
    const stop = new AbortController();
    getMagazine(dreamId, stop.signal).then(setMagazine).catch(() => { /* none yet, or not reachable: no button */ });
    return () => stop.abort();
  }, [dreamId, hasPanels]);
  return magazine;
}

type Sheet = { kind: 'cover' } | { kind: 'page'; page: MagazinePage } | { kind: 'colophon' };

function Figure({ panel, eager }: { panel: Panel | undefined; eager: boolean }) {
  if (!panel) return null;
  return <figure className="mag-figure"><Picture panel={panel} className="mag-picture" alt={panel.caption} eager={eager} />{panel.caption && <figcaption>{panel.caption}</figcaption>}</figure>;
}

function SheetView({ sheet, magazine, eager }: { sheet: Sheet; magazine: MagazineData; eager: boolean }) {
  const { spec, panels } = magazine;
  if (sheet.kind === 'cover') {
    const panel = panels[spec.cover.panel];
    return <div className="mag-cover" style={{ backgroundColor: spec.cover.color || undefined }}>
      {panel && <Picture panel={panel} className="mag-cover-picture" eager />}
      <div className="mag-cover-title"><small>{day(spec.colophon.dated)}</small><h2>{spec.cover.title}</h2></div>
    </div>;
  }
  if (sheet.kind === 'colophon') {
    const c = spec.colophon;
    const rows: [string, ReactNode][] = [[text.dreamt, day(c.dated)], [text.style, tr.styles[c.style as keyof typeof tr.styles] ?? c.style]];
    if (c.emotions.length) rows.push([text.felt, c.emotions.join(', ')]);
    if (c.tags.length) rows.push([text.tags, c.tags.join(', ')]);
    return <div className="mag-colophon"><h2>{spec.cover.title}</h2><dl>{rows.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl></div>;
  }
  const { page } = sheet;
  if (page.layout === 'quote') return <blockquote className="mag-quote">{page.text}</blockquote>;
  return <div className={`mag-page mag-${page.layout}`}>{page.panels.map(i => <Figure key={i} panel={panels[i]} eager={eager} />)}</div>;
}

/** G5: reads a magazine page by page; buttons, arrow keys and swipes turn pages, Escape closes. */
export default function Magazine({ magazine, onClose }: { magazine: MagazineData; onClose: () => void }) {
  const sheets: Sheet[] = [{ kind: 'cover' }, ...magazine.spec.pages.map(page => ({ kind: 'page' as const, page })), { kind: 'colophon' }];
  const [at, setAt] = useState(0);
  const [way, setWay] = useState<'forward' | 'back'>('forward');
  const dialog = useRef<HTMLDivElement>(null);
  const start = useRef<number | null>(null);
  const last = sheets.length - 1;

  const turn = (to: number) => {
    if (to < 0 || to > last || to === at) return;
    setWay(to > at ? 'forward' : 'back');
    setAt(to);
  };

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    dialog.current?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = overflow; opener?.focus?.(); };
  }, []);

  useEffect(() => {  // the next pictures are already on their way when the page turns
    for (const sheet of sheets.slice(at + 1, at + 3)) {
      const ids = sheet.kind === 'page' ? sheet.page.panels : [];
      for (const i of ids) { const p = magazine.panels[i]; if (p?.url) new Image().src = p.url; }
    }
  }, [at]); // eslint-disable-line react-hooks/exhaustive-deps

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
    else if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { e.preventDefault(); turn(at + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); turn(at - 1); }
    else if (e.key === 'Home') turn(0);
    else if (e.key === 'End') turn(last);
  };

  return createPortal(<div className="reader" role="dialog" aria-modal="true" aria-label={magazine.spec.cover.title} tabIndex={-1} ref={dialog} onKeyDown={onKey}>
    <header className="reader-bar">
      <button className="reader-close" onClick={onClose} aria-label={text.close}><Icon name="chevron" /></button>
      <span className="reader-count" aria-live="polite">{text.page(at + 1, sheets.length)}</span>
    </header>
    <div className="reader-stage"
      onPointerDown={e => { start.current = e.clientX; }}
      onPointerUp={e => { if (start.current === null) return; const dx = e.clientX - start.current; start.current = null; if (Math.abs(dx) > SWIPE) turn(at + (dx < 0 ? 1 : -1)); }}
      onPointerCancel={() => { start.current = null; }}>
      <div key={at} className={`reader-sheet turn-${way}`}><SheetView sheet={sheets[at]} magazine={magazine} eager /></div>
    </div>
    <nav className="reader-turns" aria-label={text.label}>
      <button onClick={() => turn(at - 1)} disabled={at === 0} aria-label={text.prev}><Icon name="chevron" /></button>
      <button onClick={() => at === last ? onClose() : turn(at + 1)} aria-label={at === last ? text.close : text.next}>{at === last ? <Icon name="check" /> : <Icon name="chevron" className="flip" />}</button>
    </nav>
  </div>, document.body);  // outside the page: its entry animation would hold a fixed layer inside it
}
