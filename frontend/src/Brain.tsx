import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { editBrain, getBrain, type Brain as BrainData, type BrainLink, type Relation } from './api';
import engraving from './assets/brain/engraving.webp';
import { BRAIN_IMAGE, RIDGES } from './brainRidges';
import { BRAIN_REGIONS, pickRidges, type RegionId } from './brainShape';
import { tr } from './strings';

// BG3: the dreamer's dreams on an engraved brain. Each dream is a small light on a gyrus, oldest at the front of
// the brain; links curve between them, coloured by relation type (BG1). The brain leans toward the finger and a
// soft light follows it. Points are buttons, links an SVG over the picture; no graph library.

export const RELATION_COLORS: Record<Relation, string> = {
  shares_content: '#86a8ff', shares_concept: '#f3c84b', shares_emotion: '#f29bbb', near_in_time: '#cfd6e6', series: '#ffffff',
};
const EMOTION_COLORS: Record<string, string> = {
  anger: '#ef7d63', apprehension: '#a99cff', sadness: '#79b3e6', confusion: '#f3c84b', happiness: '#9bdc9a',
};
const { width: W, height: H } = BRAIN_IMAGE;

function evidenceText(l: BrainLink) {
  if (l.relation === 'near_in_time') return tr.brain.daysApart(l.evidence.days ?? 0);
  return (l.evidence.shared ?? []).map((s) => s.label).slice(0, 4).join(', ');
}

/** A link bows a little toward the middle of the brain, like a path through it. */
function curve(a: { x: number; y: number }, b: { x: number; y: number }) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2, cx = mx + (W * .46 - mx) * .35, cy = my + (H * .42 - my) * .35;
  return `M${a.x.toFixed(0)} ${a.y.toFixed(0)} Q${cx.toFixed(0)} ${cy.toFixed(0)} ${b.x.toFixed(0)} ${b.y.toFixed(0)}`;
}

export default function Brain({ onTell, regions = [] }: { onTell: () => void; regions?: RegionId[] }) {
  const [data, setData] = useState<BrainData | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);
  const linkingRef = useRef<string | null>(null);
  linkingRef.current = linking ? selected : null;
  const choose = (id: string | null) => {  // while linking, the next dream tapped is the other end
    const from = linkingRef.current;
    if (from && id && id !== from) { setLinking(false); editBrain(from, id, 'link').then(setData).catch((cause) => setError(cause instanceof Error ? cause.message : tr.genericError)); return; }
    if (!from) setSelected(id);
  };
  const [hidden, setHidden] = useState<Set<Relation>>(new Set());
  const frame = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const moved = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    getBrain(controller.signal).then(setData).catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : tr.genericError); });
    return () => controller.abort();
  }, []);

  const links = useMemo(() => (data?.links ?? []).filter((l) => !hidden.has(l.relation)), [data, hidden]);
  const byId = useMemo(() => new Map((data?.dreams ?? []).map((d) => [d.id, d])), [data]);
  const spots = useMemo(() => {
    if (!data) return new Map<string, { x: number; y: number }>();
    const ordered = [...data.dreams].sort((a, b) => a.dated.localeCompare(b.dated) || a.id.localeCompare(b.id));
    const places = pickRidges(RIDGES, ordered.length);
    return new Map(ordered.map((d, i) => [d.id, places[i]]));
  }, [data]);
  const neighbours = useMemo(() => {
    if (!selected) return null;
    return new Set(links.flatMap((l) => (l.source === selected ? [l.target] : l.target === selected ? [l.source] : [])));
  }, [links, selected]);

  // Touch: one finger moves the brain, two pinch, the wheel zooms; the brain leans and the light follows the pointer.
  useEffect(() => {
    const box = frame.current, inner = stage.current;
    if (!box || !inner) return;
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const view = { x: 0, y: 0, k: 1 }, lean = { x: 0, y: 0 };
    const pointers = new Map<number, { x: number; y: number }>();
    let pinch = 0, travel = 0, raf = 0;
    const apply = () => {
      raf = 0;
      inner.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k}) rotateX(${lean.y * -5}deg) rotateY(${lean.x * 7}deg)`;
    };
    const ask = () => { if (!raf) raf = requestAnimationFrame(apply); };
    const light = (e: PointerEvent) => {
      const r = box.getBoundingClientRect();
      const nx = (e.clientX - r.left) / r.width, ny = (e.clientY - r.top) / r.height;
      box.style.setProperty('--mx', `${(nx * 100).toFixed(1)}%`); box.style.setProperty('--my', `${(ny * 100).toFixed(1)}%`);
      if (!still) { lean.x = nx * 2 - 1; lean.y = ny * 2 - 1; ask(); }
    };
    const down = (e: PointerEvent) => {
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pointers.size === 1) { travel = 0; moved.current = false; }
      if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); }
    };
    const move = (e: PointerEvent) => {
      light(e);
      const last = pointers.get(e.pointerId);
      if (!last) return;
      const dx = e.clientX - last.x, dy = e.clientY - last.y;
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      travel += Math.abs(dx) + Math.abs(dy);
      if (travel > 8 && !moved.current) { moved.current = true; box.setPointerCapture(e.pointerId); }
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) view.k = Math.min(4, Math.max(1, view.k * d / pinch));
        pinch = d;
      } else if (moved.current) { view.x += dx; view.y += dy; }
      const room = box.clientWidth * (view.k - .6);  // never lose the brain off screen
      view.x = Math.max(-room, Math.min(room, view.x)); view.y = Math.max(-room, Math.min(room, view.y));
      ask();
    };
    const up = (e: PointerEvent) => { pointers.delete(e.pointerId); if (pointers.size < 2) pinch = 0; };
    const leave = () => { lean.x = lean.y = 0; ask(); };
    const wheel = (e: WheelEvent) => { e.preventDefault(); view.k = Math.min(4, Math.max(1, view.k * Math.exp(-e.deltaY * .0015))); if (view.k === 1) view.x = view.y = 0; ask(); };
    box.addEventListener('pointerdown', down); box.addEventListener('pointermove', move);
    box.addEventListener('pointerup', up); box.addEventListener('pointercancel', up); box.addEventListener('pointerleave', leave);
    box.addEventListener('wheel', wheel, { passive: false });
    apply();
    return () => {
      cancelAnimationFrame(raf);
      box.removeEventListener('pointerdown', down); box.removeEventListener('pointermove', move);
      box.removeEventListener('pointerup', up); box.removeEventListener('pointercancel', up); box.removeEventListener('pointerleave', leave);
      box.removeEventListener('wheel', wheel);
    };
  }, [data]);

  const focus = regions.map((id) => BRAIN_REGIONS[id]);
  const regionMask = focus.length ? focus.map((r) => `radial-gradient(${(r.rx / W * 100).toFixed(1)}% ${(r.ry / H * 100).toFixed(1)}% at ${(r.x / W * 100).toFixed(1)}% ${(r.y / H * 100).toFixed(1)}%, #000 70%, transparent 100%)`).join(', ') : '';

  if (error) return <section className="brain brain-state"><p role="alert">{error}</p></section>;
  if (!data) return <section className="brain brain-state"><p role="status">{tr.brain.loading}</p></section>;
  if (!data.dreams.length) return <section className="brain brain-state"><p>{tr.brain.empty}</p><button className="brain-tell" onClick={onTell}>{tr.brain.tell}</button></section>;

  const chosen = selected ? byId.get(selected) : undefined;
  const chosenLinks = chosen ? links.filter((l) => l.source === chosen.id || l.target === chosen.id) : [];
  const toggle = (r: Relation) => setHidden((h) => { const next = new Set(h); if (next.has(r)) next.delete(r); else next.add(r); return next; });

  return <section className={chosen ? "brain picked" : "brain"} aria-label={tr.brain.label}>
    <div ref={frame} className="brain-frame" aria-hidden="true" onClick={() => { if (!moved.current) choose(null); }}>
      <div ref={stage} className="brain-stage" style={{ aspectRatio: `${W} / ${H}` }}>
        {focus.length > 0 && <img src={engraving} alt="" className="brain-art brain-art-dim" draggable={false} />}
        <img src={engraving} alt="" className="brain-art" draggable={false} style={regionMask ? { WebkitMaskImage: regionMask, maskImage: regionMask } : undefined} />
        <svg className="brain-links" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          {links.map((l) => {
            const a = spots.get(l.source), b = spots.get(l.target);
            if (!a || !b) return null;
            const lit = !selected || l.source === selected || l.target === selected;
            return <path key={`${l.relation}${l.source}${l.target}`} d={curve(a, b)} className={selected && lit ? 'flow' : lit ? '' : 'dim'}
              stroke={RELATION_COLORS[l.relation]} strokeWidth={1.6 + 3.2 * l.weight} strokeOpacity={lit ? .3 + .6 * l.weight : .06}
              strokeDasharray={l.relation === 'near_in_time' ? '6 9' : undefined} />;
          })}
        </svg>
        {data.dreams.map((d, i) => {
          const p = spots.get(d.id);
          if (!p) return null;
          const lit = !selected || d.id === selected || neighbours?.has(d.id);
          return <button key={d.id} tabIndex={-1} className={`brain-dot${d.id === selected ? ' on' : ''}${lit ? '' : ' dim'}${d.degree ? '' : ' alone'}`}
            style={{ left: `${(p.x / W * 100).toFixed(2)}%`, top: `${(p.y / H * 100).toFixed(2)}%`, ['--tint' as string]: EMOTION_COLORS[d.emotions[0]] ?? '#f6f1e6', ['--size' as string]: `${(6 + Math.sqrt(d.degree) * 2.4).toFixed(1)}px`, animationDelay: `${(i * .37) % 4}s` } as CSSProperties}
            onClick={(e) => { e.stopPropagation(); if (!moved.current) choose(d.id); }}>
            {d.id === selected && <span className="brain-name">{d.title || tr.brain.untitled}</span>}
          </button>;
        })}
      </div>
    </div>
    <div className="brain-legend" role="group" aria-label={tr.brain.filter}>
      {data.relations.map((r) => <button key={r} aria-pressed={!hidden.has(r)} onClick={() => toggle(r)}>
        <span className={r === 'near_in_time' ? 'swatch dashed' : 'swatch'} style={{ color: RELATION_COLORS[r] }} />{tr.brain.relations[r]}
      </button>)}
    </div>
    <ul className="brain-sr">
      {data.dreams.map((d) => <li key={d.id}><button onClick={() => choose(d.id)}>{d.title || tr.brain.untitled}, {tr.brain.linkCount(d.degree)}</button></li>)}
    </ul>
    {chosen && <aside className="brain-card" aria-live="polite">
      {chosen.thumbnail && <img src={chosen.thumbnail} alt="" />}
      <div className="brain-card-body">
        <h2>{chosen.title || tr.brain.untitled}</h2>
        <time dateTime={chosen.dated}>{new Date(`${chosen.dated}T12:00:00`).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })}</time>
        {chosenLinks.length ? <ul>{chosenLinks.map((l) => {
          const other = byId.get(l.source === chosen.id ? l.target : l.source);
          return <li key={`${l.relation}${l.source}${l.target}`}>
            <button onClick={() => other && setSelected(other.id)}>
              <span className="swatch" style={{ color: RELATION_COLORS[l.relation] }} aria-hidden="true" />
              <strong>{other?.title || tr.brain.untitled}</strong><small>{tr.brain.relations[l.relation]}{l.relation === 'series' ? '' : ` · ${evidenceText(l)}`}</small>
            </button>
            {other && <button className="brain-unlink" aria-label={l.relation === 'series' ? tr.brain.unlink : tr.brain.hide}
              onClick={() => editBrain(chosen.id, other.id, l.relation === 'series' ? 'link' : 'hide', l.relation !== 'series').then(setData).catch((cause) => setError(cause instanceof Error ? cause.message : tr.genericError))}>×</button>}
          </li>;
        })}</ul> : <p>{tr.brain.floating}</p>}
        {linking ? <p className="brain-pick">{tr.brain.pick} <button onClick={() => setLinking(false)}>{tr.brain.cancel}</button></p>
          : data.dreams.length > 1 && <button className="brain-connect" onClick={() => setLinking(true)}>{tr.brain.connect}</button>}
      </div>
      <button className="brain-close" onClick={() => { setLinking(false); setSelected(null); }} aria-label={tr.brain.close}>×</button>
    </aside>}
  </section>;
}
