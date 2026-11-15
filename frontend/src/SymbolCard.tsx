import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { getSymbol, type SymbolCard as Card } from './api';
import Icon from './Icon';
import { tr } from './strings';

// F1: what the traditions say about one symbol, with their sources, and how often it comes back to the reader.
export default function SymbolCard({ id, onClose }: { id: string; onClose: () => void }) {
  const [card, setCard] = useState<Card | null>(null);
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDivElement>(null);
  const text = tr.symbolCard;

  useEffect(() => {
    const controller = new AbortController();
    getSymbol(id, controller.signal).then(setCard).catch((cause) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : tr.genericError);
    });
    dialog.current?.focus();
    return () => controller.abort();
  }, [id]);

  return createPortal(<div className="symbol-card-backdrop" onClick={onClose}>
    <div className="symbol-card" role="dialog" aria-modal="true" aria-label={card?.label ?? text.loading} tabIndex={-1} ref={dialog}
      onClick={(e) => e.stopPropagation()} onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}>
      <button className="symbol-card-close" onClick={onClose} aria-label={text.close}><Icon name="chevron" /></button>
      {error ? <p className="error">{error}</p> : !card ? <p role="status">{text.loading}</p> : <>
        <header>
          {card.glyph && <img src={card.glyph} alt="" />}
          <h2>{card.label}</h2>
          <p>{card.mine > 0 ? text.mine(card.mine) : text.first}</p>
        </header>
        {card.meanings.length > 0 && <ul className="symbol-meanings">
          {card.meanings.map((m, i) => <li key={i}>
            <p>{m.text}</p>
            <small>{[text.traditions[m.tradition] ?? m.tradition, m.author || m.source, m.locator].filter(Boolean).join(' · ')}</small>
          </li>)}
        </ul>}
        {card.others && <p className="symbol-others">{text.others(text.emotions[card.others.emotion] ?? card.others.emotion, card.others.people)}</p>}
      </>}
    </div>
  </div>, document.body);
}
