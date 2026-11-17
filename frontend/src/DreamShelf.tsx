import { useLayoutEffect, useRef } from 'react';
import type { Dream } from './api';
import Picture from './Picture';
import { SHELF, shelfPose } from './shelf';
import { tr } from './strings';

/** The library as a stack of dream cases: each one a cover with a title band, like tapes on a shelf seen in
 * perspective. The case in the middle of the screen faces the reader; the others tip away as they scroll off.
 * Tapping a tipped case brings it to the middle, tapping the middle one opens it. Without motion: a flat stack. */
// one colour per feeling, so a shelf of calm dreams reads differently from a shelf of fearful ones
const TINTS: Record<string, string> = {
  huzur: '#c7e8c4', sevinç: '#ffd8a8', mutluluk: '#ffd8a8', merak: '#8fd8ff', şaşkınlık: '#b9a6ff', özlem: '#f2c4cf',
  korku: '#a7a3d9', kaygı: '#a7a3d9', üzüntü: '#9cc2e6', öfke: '#f2a48f', utanç: '#e6b8d0',
};
const SPARE = ['#f2c4cf', '#b9a6ff', '#8fd8ff', '#c7e8c4', '#ffd8a8', '#cfd3e6'];
const day = (d: Dream) => new Date(d.journal?.dreamedOn ? d.journal.dreamedOn + 'T12:00:00' : d.createdAt)
  .toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
const tintOf = (d: Dream) => {
  const top = ([...d.emotions].filter(e => e.pct > 0).sort((a, b) => b.pct - a.pct)[0]?.label ?? '').toLocaleLowerCase('tr-TR').trim();
  if (TINTS[top]) return TINTS[top];
  let h = 0; for (const c of top) h = (h * 31 + c.charCodeAt(0)) | 0;
  return top ? SPARE[Math.abs(h) % SPARE.length] : '#cfd3e6';
};

export default function DreamShelf({ dreams, onOpen }: { dreams: Dream[]; onOpen: (dream: Dream) => void }) {
  const list = useRef<HTMLOListElement>(null);

  useLayoutEffect(() => {
    const el = list.current;
    if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let frame = 0;
    const pose = () => {
      frame = 0;
      const half = window.innerHeight / 2;
      for (const item of el.children as HTMLCollectionOf<HTMLElement>) {
        const box = item.getBoundingClientRect();
        const p = shelfPose(box.top + box.height / 2 - half, half);
        const card = item.firstElementChild as HTMLElement;
        card.style.transform = `translateZ(${p.depth.toFixed(1)}px) rotateX(${p.angle.toFixed(2)}deg)`;
        card.style.opacity = p.fade.toFixed(3);
        item.style.zIndex = String(p.layer);
        item.classList.toggle('front', p.front);
        item.style.setProperty('--below', p.below.toFixed(3));
      }
    };
    const ask = () => { if (!frame) frame = requestAnimationFrame(pose); };
    pose();
    window.addEventListener('scroll', ask, { passive: true });
    window.addEventListener('resize', ask);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', ask); window.removeEventListener('resize', ask); };
  }, [dreams]);

  const choose = (dream: Dream, item: HTMLElement) => {
    if (item.classList.contains('front') || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { onOpen(dream); return; }
    const box = item.getBoundingClientRect();
    window.scrollBy({ top: box.top + box.height / 2 - window.innerHeight / 2, behavior: 'smooth' });
  };

  return <ol ref={list} className="shelf" style={{ ['--step' as string]: `${SHELF.step}px`, ['--case' as string]: `${SHELF.height}px` }}>
    {dreams.map(dream => {
      const panel = dream.panels.find(p => p.url);
      return <li key={dream.id}>
        <button className={panel ? 'case' : 'case paper'} style={{ ['--tint' as string]: tintOf(dream) }} onClick={e => choose(dream, e.currentTarget.parentElement!)}>
          <span className="case-band"><b>{dream.title || tr.brain.untitled}</b><small>{day(dream)}</small></span>
          {panel ? <Picture panel={panel} className="case-cover" thumb /> : <span className="case-cover case-words">{dream.originalText.slice(0, 160)}</span>}
          <span className="case-band case-foot" aria-hidden="true"><b>{dream.title || tr.brain.untitled}</b><small>{day(dream)}</small></span>
          <span className="case-edge" aria-hidden="true" />
        </button>
      </li>;
    })}
  </ol>;
}
