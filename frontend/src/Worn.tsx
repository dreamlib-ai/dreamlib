import { Fragment } from 'react';

/** Worn heading: letters stay on one straight line (Cenker: no bouncing letters), each with slightly its own
 * ink, and a faintly worn edge from the #worn SVG filter, added to the page once. Screen readers get plain text. */
const FILTER = '<svg id="worn-defs" width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="worn" x="-4%" y="-12%" width="108%" height="124%">'
  + '<feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="4" result="n"/>'
  + '<feDisplacementMap in="SourceGraphic" in2="n" scale="0.8" xChannelSelector="R" yChannelSelector="G" result="d"/>'
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
      return <span key={i} style={{ opacity: (0.9 + jitter(i + 3) * 0.1).toFixed(2) }}>{ch}</span>;
    })}</span></Fragment>)}
  </span></span>;
}
