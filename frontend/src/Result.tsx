import { useState, type ReactNode } from 'react';
import type { Analysis } from './api';
import { tr } from './strings';
import { effectiveFeatures } from './features';
import SymbolCard from './SymbolCard';

type Part = NonNullable<Analysis['segments']>[number];

/** The reading split into paragraphs at blank lines; a symbol never breaks across two. */
export function paragraphs(parts: Part[]): Part[][] {
  const out: Part[][] = [[]];
  for (const part of parts) {
    if (part.entity) { out[out.length - 1].push(part); continue; }
    part.text.split(/\n\s*\n/).forEach((piece, i) => {
      if (i > 0) out.push([]);
      if (piece) out[out.length - 1].push({ text: piece });
    });
  }
  return out.filter(p => p.some(part => part.text.trim()));
}

// The interpretation of one dream; used right after telling it and when opening it from the library.
export default function Result({ analysis, children, after, traces = true }: { analysis: Analysis; children?: ReactNode; after?: ReactNode; traces?: boolean }) {
  const features = effectiveFeatures(analysis);
  const [open, setOpen] = useState<string | null>(null);  // F1: the symbol whose card is open
  const parts = analysis.segments?.length ? analysis.segments : [{ text: analysis.interpretation }];
  return (
    <section className="result reading rise">
      <h2>{analysis.title}</h2>
      <div className="reading-text">
        {paragraphs(parts).map((paragraph, p) => <p key={p}>{paragraph.map((part, i) => part.entity
          ? <button key={i} type="button" className="symbol-mention" aria-label={tr.symbolCard.open(part.text)} onClick={() => setOpen(part.entity!)}>{part.text}{part.glyph && <img src={part.glyph} alt="" />}</button>
          : <span key={i}>{part.text}</span>)}</p>)}
      </div>
      {traces && <div className="traces">
        {features.tags.length > 0 && <div className="tags">{features.tags.map((t) => <span key={t} className="tag">{t}</span>)}</div>}
        {(features.genres.length > 0 || features.experiences.length > 0 || features.perspective !== 'unknown') && <p className="classification-line">
          {features.genres.length > 0 && <span>{tr.classification.genreLabels[features.genres[0]]}{features.genres.slice(1).map(key => `, ${tr.classification.genreLabels[key]}`).join('')}</span>}
          {features.perspective !== 'unknown' && <span>{tr.classification.perspectiveLabels[features.perspective]}</span>}
          {features.experiences.map(key => <span key={key}>{tr.classification.experienceLabels[key]}</span>)}
          <small>{features.genreSource === 'user' || features.perspectiveSource === 'user' || features.experienceSource === 'user' ? tr.classification.user : tr.classification.model}</small>
        </p>}
        {analysis.emotions.length > 0 && <section className="trace-block"><h3>{tr.emotions}</h3>
          <ul className="emotion-chips">
            {analysis.emotions.map((e) => <li key={e.label} style={{ ['--share' as string]: `${Math.min(100, Math.max(0, e.pct))}%` }}><span>{e.label}</span><b>%{e.pct}</b></li>)}
          </ul>
        </section>}
        {analysis.objects.length > 0 && <section className="trace-block"><h3>{tr.objects}</h3>
          <dl className="objects">
            {analysis.objects.map((o) => <div key={o.label} className="obj"><dt>{o.label}</dt><dd>{o.meaning}</dd></div>)}
          </dl>
        </section>}
      </div>}
      {after}
      {open && <SymbolCard id={open} onClose={() => setOpen(null)} />}
      {children}
    </section>
  );
}
