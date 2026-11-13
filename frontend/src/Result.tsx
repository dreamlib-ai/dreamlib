import type { ReactNode } from 'react';
import type { Analysis } from './api';
import { tr } from './strings';
import { effectiveFeatures } from './features';

// The interpretation of one dream; used right after telling it and when opening it from the library.
export default function Result({ analysis, children }: { analysis: Analysis; children?: ReactNode }) {
  const features = effectiveFeatures(analysis);
  return (
    <section className="result rise">
      <h2>{analysis.title}</h2>
      <div className="tags">
        {features.tags.map((t) => (
          <span key={t} className="tag">
            {t}
          </span>
        ))}
      </div>
      <p className="lead">{analysis.interpretation}</p>
      {(features.genres.length > 0 || features.experiences.length > 0 || features.perspective !== 'unknown') && <details className="result-details"><summary>{tr.classification.heading}</summary>
        {features.genres.length > 0 && <p className="classification-line"><span>{tr.classification.genreLabels[features.genres[0]]}{features.genres.slice(1).map(key => `, ${tr.classification.genreLabels[key]}`).join('')}</span><small>{features.genreSource === 'user' ? tr.classification.user : tr.classification.model}</small></p>}
        {features.perspective !== 'unknown' && <p className="classification-line"><span>{tr.classification.perspectiveLabels[features.perspective]}</span><small>{features.perspectiveSource === 'user' ? tr.classification.user : tr.classification.model}</small></p>}
        {features.experiences.map(key => <p className="classification-line" key={key}><span>{tr.classification.experienceLabels[key]}</span><small>{features.experienceSource === 'user' ? tr.classification.user : tr.classification.narrative}</small></p>)}
      </details>}

      <details className="result-details"><summary>{tr.objects}</summary>
      <div className="objects">
        {analysis.objects.map((o) => (
          <article key={o.label} className="obj">
            <b>{o.label}</b>
            <p>{o.meaning}</p>
          </article>
        ))}
      </div>

      </details>
      <details className="result-details"><summary>{tr.emotions}</summary>
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

      </details>
      {children}
    </section>
  );
}
