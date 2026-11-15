import { useMemo } from 'react';
import { tr } from './strings';

/** While the booklet is drawn: dream dust drifts in onto a sheet of paper, gathers in a band of cloud,
 * and the page's panel lines appear one by one as panels finish. Pure CSS; reduced motion shows it still. */
export default function Drawing({ count, done, eta }: { count: number; done: number; eta?: number }) {
  const dust = useMemo(() => Array.from({ length: 26 }, (_, i) => {
    const angle = (i / 26) * Math.PI * 2 + Math.random() * .4, far = 120 + Math.random() * 90;
    return { x: Math.cos(angle) * far, y: Math.sin(angle) * far * 1.3, delay: -Math.random() * 3.2, size: 2 + Math.random() * 3, tone: i % 3 };
  }), []);
  const cols = count === 4 ? 2 : 3;
  return <div className="drawing" role="status" aria-live="polite">
    <div className="drawing-paper" style={{ ['--cols' as string]: cols }}>
      <div className="drawing-band" aria-hidden="true"><div className="cloud-fill"><i /><i /></div></div>
      <div className="drawing-frames" aria-hidden="true">
        {Array.from({ length: count }, (_, i) => <span key={i} className={i < done ? 'frame drawn' : i === done ? 'frame now' : 'frame'} style={{ ['--i' as string]: i }} />)}
      </div>
      <div className="drawing-dust" aria-hidden="true">
        {dust.map((d, i) => <i key={i} className={`tone-${d.tone}`} style={{ ['--x' as string]: `${d.x}px`, ['--y' as string]: `${d.y}px`, ['--s' as string]: `${d.size}px`, animationDelay: `${d.delay}s` }} />)}
      </div>
    </div>
    <p>{tr.app.progress}{eta ? ` · ${tr.app.remaining(eta)}` : ''}</p>
  </div>;
}
