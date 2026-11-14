import { useState } from 'react';
import { decodeBlurhash } from './blurhash';
import type { Panel } from './api';

/** What a picture needs to be drawn: an owner's panel or a shared magazine's picture (G6). */
type Shown = Pick<Panel, 'url' | 'thumb' | 'width' | 'height' | 'color' | 'blurhash'>;

const placeholders = new Map<string, string>();
/** A 32×32 picture of the BlurHash, drawn once per hash. */
export function placeholder(hash: string): string {
  if (!hash) return '';
  const known = placeholders.get(hash);
  if (known !== undefined) return known;
  let url = '';
  const pixels = decodeBlurhash(hash, 32, 32);
  const canvas = pixels ? document.createElement('canvas') : null;
  const ctx = canvas?.getContext('2d');
  if (pixels && canvas && ctx) {
    canvas.width = canvas.height = 32;
    ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels), 32, 32), 0, 0);
    url = canvas.toDataURL();
  }
  placeholders.set(hash, url);
  return url;
}

/** A stored picture at its real shape: dominant colour and BlurHash first, the picture fades in over them (G3). */
export default function Picture({ panel, className, alt = '', thumb = false, eager = false }: { panel: Shown; className: string; alt?: string; thumb?: boolean; eager?: boolean }) {
  const [shown, setShown] = useState(false);
  const hash = placeholder(panel.blurhash ?? '');
  const ratio = panel.width && panel.height ? `${panel.width} / ${panel.height}` : '1 / 1';
  const shape = panel.width && panel.height ? panel.width / panel.height : 1;
  return <span className={className} style={{ aspectRatio: ratio, ['--shape' as string]: shape, backgroundColor: panel.color || undefined, backgroundImage: hash ? `url(${hash})` : undefined }}>
    <img src={(thumb && panel.thumb) || panel.url} alt={alt} loading={eager ? 'eager' : 'lazy'} decoding="async" className={shown ? 'shown' : ''} onLoad={() => setShown(true)} />
  </span>;
}
