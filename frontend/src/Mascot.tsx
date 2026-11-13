import { useState } from 'react';
import { tr } from './strings';
import wideCloud from './assets/koala-cloud-wide.webp';
import curious from './assets/koala-curious-left.webp';
import sleepCutout from './assets/koala-sleep-cutout.webp';

type Theme = 'cloud' | 'curious' | 'sleep';

export default function Mascot({ theme = 'curious', className = '', scene = false, interactive = false }: { scene?: boolean; theme?: Theme; className?: string; interactive?: boolean }) {
  const [greeting, setGreeting] = useState(false);
  const art = scene ? (theme === 'curious' ? curious : wideCloud) : sleepCutout;
  const classes = `mascot ${scene ? 'mascot-scene' : 'mascot-cutout'} mascot-${theme} ${className} ${greeting ? 'mascot-hello' : ''}`;
  const image = !scene && theme !== 'sleep' ? <span className="mascot-actor" aria-hidden="true"><span className="mascot-frame" /></span> : <img src={art} alt="" draggable={false} />;
  if (interactive) return <button type="button" className={classes} aria-label={tr.mascot.greet} onClick={() => setGreeting(value => !value)} onAnimationEnd={event => { if (event.animationName === 'koala-greeting') setGreeting(false); }}>{image}</button>;
  return <div className={classes} aria-hidden="true">{image}</div>;
}
