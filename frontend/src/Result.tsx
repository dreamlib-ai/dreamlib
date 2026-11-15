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
export default function Result({ analysis, children, after }: { analysis: Analysis; children?: ReactNode; after?: ReactNode }) {
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
      {after}
      {open && <SymbolCard id={open} onClose={() => setOpen(null)} />}
      {children}
      <div className="reading-more">
      {features.tags.length > 0 && <div className="tags">{features.tags.map((t) => <span key={t} className="tag">{t}</span>)}</div>}
      {(features.genres.length > 0 || features.experiences.length > 0 || features.perspective !== 'unknown') && <details className="result-details"><summary>{tr.classification.heading}</summary>
        {features.genres.length > 0 && <p className="classification-line"><span>{tr.classification.genreLabels[features.genres[0]]}{features.genres.slice(1).map(key => `, ${tr.classification.genreLabels[key]}`).join('')}</span><small>{features.genreSource === 'user' ? tr.classification.user : tr.classification.model}</small></p>}
        {features.perspective !== 'unknown' && <p className="classification-line"><span>{tr.classification.perspectiveLabels[features.perspective]}</span><small>{features.perspectiveSource === 'user' ? tr.classification.user : tr.classification.model}</small></p>}
        {features.experiences.map(key => <p className="classification-line" key={key}><span>{tr.classification.experienceLabels[key]}</span><small>{features.experienceSource === 'user' ? tr.classification.user : tr.classification.narrative}</small></p>)}
      </details>}

      {analysis.objects.length > 0 && <details className="result-details"><summary>{tr.objects}</summary>
      <div className="objects">
        {analysis.objects.map((o) => (
          <article key={o.label} className="obj">
            <b>{o.label}</b>
            <p>{o.meaning}</p>
          </article>
        ))}
      </div>
      </details>}
      {analysis.emotions.length > 0 && <details className="result-details"><summary>{tr.emotions}</summary>
      <p className="small">{tr.classification.emotionHint}</p>
      <ul className="emotions">
        {analysis.emotions.map((e) => (
          <li key={e.label}>
            <span>
              {e.label} <b>%{e.pct}</b>
            </span>
            <div className="bar">
              <i style={{ width: `${Math.min(100, Math.max(0, e.pct))}%` }} />
            </div>
          </li>
        ))}
      </ul>
      </details>}
      </div>
    </section>
  );
}
