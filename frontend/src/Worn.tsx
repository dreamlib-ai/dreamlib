import { Fragment } from 'react';

/** Typewriter-worn heading: every letter sits a little off its line with its own ink, like a struck key.
 * The ragged edge comes from the #worn SVG filter, added to the page once. Screen readers get the plain text. */
const FILTER = '<svg id="worn-defs" width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="worn" x="-4%" y="-12%" width="108%" height="124%">'
  + '<feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="4" result="n"/>'
  + '<feDisplacementMap in="SourceGraphic" in2="n" scale="1.4" xChannelSelector="R" yChannelSelector="G" result="d"/>'
  + '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="9" result="s"/>'
  + '<feColorMatrix in="s" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -4.5 3.4" result="holes"/>'
  + '<feComposite in="d" in2="holes" operator="in"/></filter></svg>';
if (typeof document !== 'undefined') { document.getElementById('worn-defs')?.remove(); document.body.insertAdjacentHTML('beforeend', FILTER); }

const jitter = (i: number) => { const x = Math.sin(i * 12.9898) * 43758.5453; return x - Math.floor(x); };

export default function Worn({ text }: { text: string }) {
  let n = 0;
  return <span className="worn"><span className="sr-only">{text}</span><span aria-hidden="true">
    {text.split(' ').map((word, w) => <Fragment key={w}>{w > 0 && ' '}<span className="worn-word">{[...word].map(ch => {
      const i = n++;
      return <span key={i} style={{ opacity: (0.8 + jitter(i + 3) * 0.2).toFixed(2), transform: `translateY(${((jitter(i * 5.7) - 0.5) * 0.05).toFixed(3)}em)` }}>{ch}</span>;
    })}</span></Fragment>)}
  </span></span>;
}
