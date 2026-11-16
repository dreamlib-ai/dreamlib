import { useEffect, useMemo, useRef, useState } from 'react';
import { editBrain, getBrain, type Brain as BrainData, type BrainDream, type BrainLink, type Relation } from './api';
import { BRAIN_BOX, BRAIN_FOLDS, BRAIN_OUTLINE, BRAIN_REGIONS, onCortex, spread, type RegionId } from './brainShape';
import { tr } from './strings';

// BG3: the dreamer's dreams on a brain seen from the side. Each dream sits on the cortex line, oldest at the front
// of the brain and newer ones further round; links curve through the inside, coloured by relation type (BG1).
// Drawn on a canvas with the outline as a Path2D; no graph library.

export const RELATION_COLORS: Record<Relation, string> = {
  shares_content: '#86a8ff', shares_concept: '#f3c84b', shares_emotion: '#f29bbb', near_in_time: '#cfd6e6', series: '#ffffff',
};
const EMOTION_COLORS: Record<string, string> = {
  anger: '#ef7d63', apprehension: '#a99cff', sadness: '#79b3e6', confusion: '#f3c84b', happiness: '#9bdc9a',
};

type Spot = { d: BrainDream; x: number; y: number; r: number };
type View = { x: number; y: number; k: number };

let cortex: { x: number; y: number }[] | null = null;
/** The cortex line as points, read once from the outline path. */
function cortexLine() {
  if (cortex) return cortex;
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', BRAIN_OUTLINE);
  const total = path.getTotalLength(), out: { x: number; y: number }[] = [];
  for (let i = 0; i <= 900; i++) { const p = path.getPointAtLength(total * i / 900); if (onCortex(p.x, p.y)) out.push({ x: p.x, y: p.y }); }
  return cortex = out;
}

/** Every dream gets a place on the line, in date order, sized by how many links it has. */
function places(dreams: BrainDream[]): Spot[] {
  const ordered = [...dreams].sort((a, b) => a.dated.localeCompare(b.dated) || a.id.localeCompare(b.id));
  const spots = spread(cortexLine(), ordered.length);
  const room = 560 / Math.max(ordered.length, 1);  // the cortex line is about 560 units long
  return ordered.map((d, i) => ({ d, x: spots[i].x, y: spots[i].y, r: Math.min(3.2 + Math.sqrt(d.degree) * 1.3, Math.max(1.6, room * .42)) }));
}

function evidenceText(l: BrainLink) {
  if (l.relation === 'near_in_time') return tr.brain.daysApart(l.evidence.days ?? 0);
  return (l.evidence.shared ?? []).map((s) => s.label).slice(0, 4).join(', ');
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
  const chooseRef = useRef(choose);
  chooseRef.current = choose;
  const [hidden, setHidden] = useState<Set<Relation>>(new Set());
  const canvas = useRef<HTMLCanvasElement>(null);
  const view = useRef<View>({ x: 0, y: 0, k: 1 });

  useEffect(() => {
    const controller = new AbortController();
    getBrain(controller.signal).then(setData).catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : tr.genericError); });
    return () => controller.abort();
  }, []);

  const links = useMemo(() => (data?.links ?? []).filter((l) => !hidden.has(l.relation)), [data, hidden]);
  const byId = useMemo(() => new Map((data?.dreams ?? []).map((d) => [d.id, d])), [data]);
  const spots = useMemo(() => data ? places(data.dreams) : [], [data]);
  const neighbours = useMemo(() => {
    if (!selected) return null;
    return new Set(links.flatMap((l) => (l.source === selected ? [l.target] : l.target === selected ? [l.source] : [])));
  }, [links, selected]);

  useEffect(() => {
    const el = canvas.current;
    if (!el || !data) return;
    const ctx = el.getContext('2d');
    if (!ctx) return;
    const outline = new Path2D(BRAIN_OUTLINE), folds = BRAIN_FOLDS.map((d) => new Path2D(d));
    const at = new Map(spots.map((s) => [s.d.id, s]));
    let frame = 0;
    // the box fitted to the canvas, below the legend; the reader's pan and zoom go on top of it
    const fit = () => {
      const cw = el.clientWidth, ch = el.clientHeight, top = 64;
      const s = Math.min(cw / BRAIN_BOX.width, (ch - top - 16) / BRAIN_BOX.height) * .94;
      return { s, ox: (cw - BRAIN_BOX.width * s) / 2, oy: top + (ch - top - BRAIN_BOX.height * s) / 2 };
    };
    const draw = () => {
      frame = 0;
      const dpr = window.devicePixelRatio || 1, cw = el.clientWidth, ch = el.clientHeight;
      if (el.width !== Math.round(cw * dpr) || el.height !== Math.round(ch * dpr)) { el.width = Math.round(cw * dpr); el.height = Math.round(ch * dpr); }
      const f = fit(), v = view.current, k = f.s * v.k;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cw, ch);
      ctx.translate(cw / 2 + v.x, ch / 2 + v.y);
      ctx.scale(v.k, v.k);
      ctx.translate(f.ox - cw / 2, f.oy - ch / 2);
      ctx.scale(f.s, f.s);
      const px = 1 / k;  // one screen pixel in box units

      // The brain: a soft inner glow, the folds, the outline; out of focus outside the chosen regions.
      const shape = () => {
        const glow = ctx.createRadialGradient(200, 150, 10, 200, 150, 210);
        glow.addColorStop(0, '#2a3f8a66'); glow.addColorStop(1, '#141f5222');
        ctx.fillStyle = glow; ctx.fill(outline);
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#cfdcf229'; ctx.lineWidth = 1.4 * px * 1.6;
        for (const fold of folds) ctx.stroke(fold);
        ctx.strokeStyle = '#cfdcf266'; ctx.lineWidth = 1.6 * px * 1.4; ctx.stroke(outline);
      };
      const focus = regions.map((id) => BRAIN_REGIONS[id]);
      if (focus.length) {
        ctx.save(); ctx.filter = `blur(${6}px)`; ctx.globalAlpha = .55; shape(); ctx.restore();
        ctx.save(); ctx.beginPath();
        for (const r of focus) ctx.ellipse(r.x, r.y, r.rx, r.ry, 0, 0, Math.PI * 2);
        ctx.clip(); shape(); ctx.restore();
      } else shape();

      // Links bow toward the middle of the brain, like paths through it.
      for (const l of links) {
        const a = at.get(l.source), b = at.get(l.target);
        if (!a || !b) continue;
        const lit = !selected || l.source === selected || l.target === selected;
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2, cx = mx + (200 - mx) * .55, cy = my + (150 - my) * .55;
        ctx.globalAlpha = lit ? 0.22 + 0.6 * l.weight : 0.05;
        ctx.strokeStyle = RELATION_COLORS[l.relation];
        ctx.lineWidth = (.8 + 1.8 * l.weight) * px * 1.3;
        ctx.setLineDash(l.relation === 'near_in_time' ? [4 * px, 5 * px] : []);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.quadraticCurveTo(cx, cy, b.x, b.y); ctx.stroke();
      }
      ctx.setLineDash([]);
      for (const s of spots) {
        const lit = !selected || s.d.id === selected || neighbours?.has(s.d.id);
        ctx.globalAlpha = lit ? (s.d.degree ? 1 : .72) : 0.18;
        const tint = EMOTION_COLORS[s.d.emotions[0]] ?? '#f6f1e6';
        ctx.shadowColor = tint; ctx.shadowBlur = (s.d.id === selected ? 22 : 9) * v.k;
        ctx.fillStyle = '#f6f1e6';
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0; ctx.lineWidth = Math.min(s.r * .5, 2.4 * px); ctx.strokeStyle = tint; ctx.stroke();
        if (lit && s.d.title && (selected ? s.d.id === selected : k > 2.4)) {
          const out = Math.hypot(s.x - 200, s.y - 150) || 1, ux = (s.x - 200) / out, uy = (s.y - 150) / out;  // the name sits outside the brain
          ctx.fillStyle = '#eef6ff'; ctx.font = `500 ${12.5 * px}px 'Funnel Sans', system-ui, sans-serif`;
          ctx.textAlign = ux < -.3 ? 'right' : ux > .3 ? 'left' : 'center'; ctx.textBaseline = uy < -.3 ? 'bottom' : uy > .3 ? 'top' : 'middle';
          ctx.fillText(s.d.title.length > 26 ? `${s.d.title.slice(0, 25)}…` : s.d.title, s.x + ux * (s.r + 6 * px), s.y + uy * (s.r + 6 * px));
        }
      }
      ctx.globalAlpha = 1;
    };
    const kick = () => { if (!frame) frame = requestAnimationFrame(draw); };
    kick();

    const toBox = (cx: number, cy: number) => {
      const box = el.getBoundingClientRect(), f = fit(), v = view.current;
      const sx = (cx - box.left - box.width / 2 - v.x) / v.k + box.width / 2, sy = (cy - box.top - box.height / 2 - v.y) / v.k + box.height / 2;
      return { x: (sx - f.ox) / f.s, y: (sy - f.oy) / f.s, unit: 1 / (f.s * v.k) };
    };
    const hit = (cx: number, cy: number) => {
      const p = toBox(cx, cy);
      let best: Spot | null = null, near = Infinity;
      for (const s of spots) { const d = Math.hypot(s.x - p.x, s.y - p.y); if (d < near && d <= s.r + 14 * p.unit) { best = s; near = d; } }
      return best;
    };
    const pointers = new Map<number, { x: number; y: number }>();
    let moved = false, pinch = 0;
    const down = (e: PointerEvent) => {
      el.setPointerCapture(e.pointerId); pointers.set(e.pointerId, { x: e.clientX, y: e.clientY }); moved = false;
      if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); }
    };
    const move = (e: PointerEvent) => {
      const last = pointers.get(e.pointerId);
      if (!last) return;
      const dx = e.clientX - last.x, dy = e.clientY - last.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const v = view.current;
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) v.k = Math.min(5, Math.max(.8, v.k * (d / pinch)));
        pinch = d;
      } else { v.x += dx; v.y += dy; }
      kick();
    };
    const up = (e: PointerEvent) => {
      pointers.delete(e.pointerId);
      if (!moved && pointers.size === 0) { const s = hit(e.clientX, e.clientY); chooseRef.current(s ? s.d.id : null); }
      if (pointers.size < 2) pinch = 0;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const v = view.current; v.k = Math.min(5, Math.max(.8, v.k * Math.exp(-e.deltaY * 0.0015))); kick();
    };
    el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    el.addEventListener('wheel', wheel, { passive: false });
    window.addEventListener('resize', kick);
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener('pointerdown', down); el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up);
      el.removeEventListener('wheel', wheel); window.removeEventListener('resize', kick);
    };
  }, [data, spots, links, selected, neighbours, regions.join()]);

  if (error) return <section className="brain brain-state"><p role="alert">{error}</p></section>;
  if (!data) return <section className="brain brain-state"><p role="status">{tr.brain.loading}</p></section>;
  if (!data.dreams.length) return <section className="brain brain-state"><p>{tr.brain.empty}</p><button className="brain-tell" onClick={onTell}>{tr.brain.tell}</button></section>;

  const chosen = selected ? byId.get(selected) : undefined;
  const chosenLinks = chosen ? links.filter((l) => l.source === chosen.id || l.target === chosen.id) : [];
  const toggle = (r: Relation) => setHidden((h) => { const next = new Set(h); if (next.has(r)) next.delete(r); else next.add(r); return next; });

  return <section className="brain" aria-label={tr.brain.label}>
    <canvas ref={canvas} className="brain-canvas" aria-hidden="true" />
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
