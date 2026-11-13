import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import Mascot from './Mascot';
import { tr } from './strings';
import './intro.css';

export default function DreamIntro({ onDone }: { onDone: () => void }) {
  const [index, setIndex] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const touch = useRef<{ x: number; y: number } | null>(null);
  const slide = tr.intro.slides[index];
  const last = index === tr.intro.slides.length - 1;
  function move(delta: number) { setIndex(value => Math.max(0, Math.min(tr.intro.slides.length - 1, value + delta))); }
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, [index]);

  return <main className={`dream-intro intro-${slide.id}`} onKeyDown={event => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); move(1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); move(-1); }
  }} onTouchStart={event => {
    const point = event.touches[0]; touch.current = { x: point.clientX, y: point.clientY };
  }} onTouchEnd={event => {
    if (!touch.current) return;
    const point = event.changedTouches[0];
    const dx = point.clientX - touch.current.x, dy = point.clientY - touch.current.y;
    if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.5) move(dx < 0 ? 1 : -1);
    touch.current = null;
  }}>
    <div className="intro-atmosphere" aria-hidden="true" />
    <header className="intro-header"><span className="intro-brand">{tr.brand}</span><button onClick={onDone}>{tr.intro.skip}</button></header>
    <section className="intro-scene" key={slide.id}>
      <div className="intro-visual" data-art={slide.art}>
        <span className="dream-orbit orbit-one" aria-hidden="true" /><span className="dream-orbit orbit-two" aria-hidden="true" />
        {slide.art === 'rem' && <svg className="rem-weave" viewBox="0 0 400 200" aria-hidden="true"><path d="M20 100C80 10 120 190 200 100S320 10 380 100"/><path d="M20 100C80 190 120 10 200 100S320 190 380 100"/></svg>}
        <Mascot theme={slide.art === 'sleep' ? 'sleep' : 'curious'} interactive className="intro-koala" />
      </div>
      <div className="intro-copy">
        {slide.planned && <p className="intro-planned">{tr.intro.planned}</p>}
        <h1 ref={heading} tabIndex={-1}>{slide.title}</h1>
        <p>{slide.body}</p>
        {slide.id === 'rem' && <a className="intro-source" href="https://www.nhlbi.nih.gov/health/sleep/stages-of-sleep" target="_blank" rel="noreferrer">{tr.intro.source}</a>}
      </div>
    </section>
    <footer className="intro-footer">
      <button className="intro-back" disabled={index === 0} onClick={() => move(-1)} aria-label={tr.back}><Icon name="chevron" /></button>
      <div className="intro-dots" aria-hidden="true">{tr.intro.slides.map((item, i) => <span key={item.id} className={i === index ? 'current' : ''} />)}</div>
      <button className="intro-next" onClick={() => last ? onDone() : move(1)}>{last ? tr.intro.start : tr.intro.next}</button>
    </footer>
  </main>;
}
