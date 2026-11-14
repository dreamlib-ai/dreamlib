import { useEffect, useMemo, useRef, useState } from 'react';
import { getBrain, type Brain as BrainData, type BrainDream, type BrainLink, type Relation } from './api';
import { tr } from './strings';

// BG3: the dreamer's dreams as a night sky. Links are coloured by relation type (BG1); a dream with no
// link drifts on an outer ring. Hand-written force layout on a canvas; no graph library.

export const RELATION_COLORS: Record<Relation, string> = {
  shares_content: '#86a8ff', shares_concept: '#f3c84b', shares_emotion: '#f29bbb', near_in_time: '#cfd6e6',
};
const EMOTION_COLORS: Record<string, string> = {
  anger: '#ef7d63', apprehension: '#a99cff', sadness: '#79b3e6', confusion: '#f3c84b', happiness: '#9bdc9a',
};

type Body = { d: BrainDream; x: number; y: number; vx: number; vy: number; r: number; free: boolean; phase: number };
type View = { x: number; y: number; k: number };

const reduced = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function bodies(data: BrainData): Body[] {
  const loose = data.dreams.filter((d) => d.degree === 0).length, held = data.dreams.length - loose;
  let li = 0, hi = 0;
  return data.dreams.map((d, i) => {
    const free = d.degree === 0;  // spread each group evenly round its own circle
    const a = free ? ((li++ + 0.5) / Math.max(loose, 1)) * Math.PI * 2 : (hi++ / Math.max(held, 1)) * Math.PI * 2;
    const dist = free ? 220 : 80 + (i % 5) * 18;
    return { d, x: Math.cos(a) * dist, y: Math.sin(a) * dist, vx: 0, vy: 0, r: 7 + Math.sqrt(d.degree) * 2.6, free, phase: i * 1.7 };
  });
}

function step(nodes: Body[], links: BrainLink[], t: number, drag: Body | null) {
  const index = new Map(nodes.map((b) => [b.d.id, b]));
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
      const f = 2200 / d2, d = Math.sqrt(d2);
      a.vx -= (f * dx) / d; a.vy -= (f * dy) / d; b.vx += (f * dx) / d; b.vy += (f * dy) / d;
    }
  }
  for (const l of links) {
    const a = index.get(l.source), b = index.get(l.target);
    if (!a || !b) continue;
    const dx = b.x - a.x, dy = b.y - a.y, d = Math.max(Math.hypot(dx, dy), 1);
    const rest = 130 - 70 * l.weight, f = (d - rest) * 0.012 * (0.4 + l.weight);
    a.vx += (f * dx) / d; a.vy += (f * dy) / d; b.vx -= (f * dx) / d; b.vy -= (f * dy) / d;
  }
  const ring = 150 + Math.sqrt(nodes.length) * 20;
  for (const b of nodes) {
    if (b === drag) { b.vx = b.vy = 0; continue; }
    if (b.free) {  // floats on the outer ring, slowly turning, a little restless
      const d = Math.max(Math.hypot(b.x, b.y), 1);
      b.vx += ((ring - d) * b.x) / d * 0.004 - (b.y / d) * 0.12 + Math.sin(t / 1400 + b.phase) * 0.03;
      b.vy += ((ring - d) * b.y) / d * 0.004 + (b.x / d) * 0.12 + Math.cos(t / 1700 + b.phase) * 0.03;
    } else {
      b.vx -= b.x * 0.004; b.vy -= b.y * 0.004;
    }
    b.vx *= 0.82; b.vy *= 0.82;
    b.x += Math.max(-12, Math.min(12, b.vx)); b.y += Math.max(-12, Math.min(12, b.vy));
  }
}

function evidenceText(l: BrainLink) {
  if (l.relation === 'near_in_time') return tr.brain.daysApart(l.evidence.days ?? 0);
  return (l.evidence.shared ?? []).map((s) => s.label).slice(0, 4).join(', ');
}

export default function Brain({ onTell }: { onTell: () => void }) {
  const [data, setData] = useState<BrainData | null>(null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Set<Relation>>(new Set());
  const canvas = useRef<HTMLCanvasElement>(null);
  const world = useRef<{ nodes: Body[]; view: View; drag: Body | null; dirty: boolean; fit: boolean }>({ nodes: [], view: { x: 0, y: 0, k: 1 }, drag: null, dirty: true, fit: true });

  useEffect(() => {
    const controller = new AbortController();
    getBrain(controller.signal).then(setData).catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : tr.genericError); });
    return () => controller.abort();
  }, []);

  const links = useMemo(() => (data?.links ?? []).filter((l) => !hidden.has(l.relation)), [data, hidden]);
  const byId = useMemo(() => new Map((data?.dreams ?? []).map((d) => [d.id, d])), [data]);
  const neighbours = useMemo(() => {
    if (!selected) return null;
    return new Set(links.flatMap((l) => (l.source === selected ? [l.target] : l.target === selected ? [l.source] : [])));
  }, [links, selected]);

  useEffect(() => {
    if (!data) return;
    world.current.nodes = bodies(data);
    if (reduced()) for (let i = 0; i < 400; i++) step(world.current.nodes, data.links, i * 16, null);
    world.current.dirty = true;
  }, [data]);

  useEffect(() => {
    const el = canvas.current;
    if (!el || !data) return;
    const ctx = el.getContext('2d');
    if (!ctx) return;
    const still = reduced();
    let frame = 0, settle = 0;
    const draw = (t: number) => {
      const w = world.current, dpr = window.devicePixelRatio || 1;
      const { clientWidth: cw, clientHeight: ch } = el;
      if (el.width !== cw * dpr || el.height !== ch * dpr) { el.width = cw * dpr; el.height = ch * dpr; }
      if (!still) { step(w.nodes, links, t, w.drag); settle++; }
      if (w.fit && w.nodes.length) {  // keep everything in frame until the dreamer zooms or pans
        const reach = Math.max(...w.nodes.map((b) => Math.hypot(b.x, b.y) + b.r)) + 24;
        const k = Math.min(1.4, Math.max(0.35, (Math.min(cw, ch - 64) / 2 - 16) / reach));
        w.view = { x: 0, y: 30, k: w.view.k + (k - w.view.k) * 0.2 };
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cw, ch);
      ctx.translate(cw / 2 + w.view.x, ch / 2 + w.view.y);
      ctx.scale(w.view.k, w.view.k);
      const at = new Map(w.nodes.map((b) => [b.d.id, b]));
      for (const l of links) {
        const a = at.get(l.source), b = at.get(l.target);
        if (!a || !b) continue;
        const lit = !selected || l.source === selected || l.target === selected;
        ctx.globalAlpha = lit ? 0.25 + 0.65 * l.weight : 0.06;
        ctx.strokeStyle = RELATION_COLORS[l.relation];
        ctx.lineWidth = (1 + 2.5 * l.weight) / Math.sqrt(w.view.k);
        ctx.setLineDash(l.relation === 'near_in_time' ? [4, 5] : []);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      ctx.setLineDash([]);
      for (const b of w.nodes) {
        const focus = !selected || b.d.id === selected || neighbours?.has(b.d.id);
        ctx.globalAlpha = focus ? (b.free ? 0.7 : 1) : 0.18;
        const tint = EMOTION_COLORS[b.d.emotions[0]] ?? '#f6f1e6';
        ctx.shadowColor = tint; ctx.shadowBlur = b.d.id === selected ? 24 : 10;
        ctx.fillStyle = '#f6f1e6';
        ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0; ctx.lineWidth = 3 / w.view.k; ctx.strokeStyle = tint; ctx.stroke();
        if (focus && (selected ? true : w.view.k > 1.3) && b.d.title) {
          ctx.fillStyle = '#f6f1e6'; ctx.font = `${12 / w.view.k}px Unbounded, system-ui, sans-serif`; ctx.textAlign = 'center';
          ctx.fillText(b.d.title.length > 28 ? `${b.d.title.slice(0, 27)}…` : b.d.title, b.x, b.y + b.r + 16 / w.view.k);
        }
      }
      ctx.globalAlpha = 1;
      w.dirty = false;
      const moving = !still && (settle < 600 || w.nodes.some((b) => b.free) || w.drag);
      frame = moving || w.dirty ? requestAnimationFrame(draw) : 0;
    };
    const kick = () => { world.current.dirty = true; if (!frame) frame = requestAnimationFrame(draw); };
    frame = requestAnimationFrame(draw);

    const toWorld = (cx: number, cy: number) => {
      const r = el.getBoundingClientRect(), v = world.current.view;
      return { x: (cx - r.left - r.width / 2 - v.x) / v.k, y: (cy - r.top - r.height / 2 - v.y) / v.k };
    };
    const hit = (cx: number, cy: number) => {
      const p = toWorld(cx, cy);
      return world.current.nodes.find((b) => Math.hypot(b.x - p.x, b.y - p.y) <= b.r + 14 / world.current.view.k) ?? null;
    };
    const pointers = new Map<number, { x: number; y: number }>();
    let moved = false, pinch = 0;
    const down = (e: PointerEvent) => {
      el.setPointerCapture(e.pointerId); pointers.set(e.pointerId, { x: e.clientX, y: e.clientY }); moved = false;
      if (pointers.size === 1) world.current.drag = hit(e.clientX, e.clientY);
      if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = Math.hypot(a.x - b.x, a.y - b.y); world.current.drag = null; }
    };
    const move = (e: PointerEvent) => {
      const last = pointers.get(e.pointerId);
      if (!last) return;
      const dx = e.clientX - last.x, dy = e.clientY - last.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const w = world.current;
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) { w.fit = false; w.view.k = Math.min(3, Math.max(0.35, w.view.k * (d / pinch))); }
        pinch = d;
      } else if (w.drag) {
        const p = toWorld(e.clientX, e.clientY); w.drag.x = p.x; w.drag.y = p.y; w.drag.free = false;
      } else { w.fit = false; w.view.x += dx; w.view.y += dy; }
      kick();
    };
    const up = (e: PointerEvent) => {
      pointers.delete(e.pointerId);
      if (!moved && pointers.size === 0) { const b = hit(e.clientX, e.clientY); setSelected(b ? b.d.id : null); }
      if (pointers.size < 2) pinch = 0;
      if (world.current.drag) { world.current.drag.free = world.current.drag.d.degree === 0; world.current.drag = null; }
      kick();
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      world.current.fit = false;
      const v = world.current.view; v.k = Math.min(3, Math.max(0.35, v.k * Math.exp(-e.deltaY * 0.0015))); kick();
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
  }, [data, links, selected, neighbours]);

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
      {data.dreams.map((d) => <li key={d.id}><button onClick={() => setSelected(d.id)}>{d.title || tr.brain.untitled}, {tr.brain.linkCount(d.degree)}</button></li>)}
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
              <strong>{other?.title || tr.brain.untitled}</strong><small>{tr.brain.relations[l.relation]} · {evidenceText(l)}</small>
            </button>
          </li>;
        })}</ul> : <p>{tr.brain.floating}</p>}
      </div>
      <button className="brain-close" onClick={() => setSelected(null)} aria-label={tr.brain.close}>×</button>
    </aside>}
  </section>;
}
