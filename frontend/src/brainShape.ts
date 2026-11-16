/** A brain seen from its left side, drawn in a 400 × 320 box: the frontal lobe on the left, the occipital pole on
 * the right, the temporal lobe below, the cerebellum and brainstem at the back. Dreams sit on the cortex line. */
export const BRAIN_BOX = { width: 400, height: 320 };

export const BRAIN_OUTLINE = 'M70 190 C40 170 30 120 55 85 C80 45 140 25 200 28 C260 30 315 55 340 95 C362 125 365 165 350 190 '
  + 'C340 205 325 212 312 214 C335 222 345 250 325 268 C305 285 265 282 250 262 C245 275 240 295 238 315 L222 315 '
  + 'C222 295 220 275 214 258 C190 250 150 252 120 240 C100 232 92 215 100 205 C90 200 80 195 70 190 Z';

/** Folds drawn faintly inside: the lateral and central sulci, a few gyri, the cerebellum's leaves. */
export const BRAIN_FOLDS = [
  'M100 205 C140 186 190 172 246 160',
  'M216 31 C206 80 200 122 190 168',
  'M150 36 C150 70 140 100 120 128',
  'M262 40 C255 70 262 100 290 120',
  'M75 120 C100 118 118 135 120 160',
  'M300 150 C318 160 330 172 340 182',
  'M150 222 C180 214 210 210 236 206',
  'M262 236 C285 232 310 236 330 246', 'M260 252 C285 248 308 252 322 260',
];

/** Places on the cortex line: the cerebellum and brainstem are left out, the dreams live on the cerebrum. */
export const onCortex = (x: number, y: number) => !(y > 204 && x > 232) && !(y > 248 && x > 205);

/** Regions to mark later (Cenker will place them); each is a soft ellipse in the same box. When some are chosen,
 * everything else is drawn out of focus. Empty for now: the layer is here so marking needs no new drawing code. */
export type RegionId = 'prefrontal' | 'motor' | 'parietal' | 'occipital' | 'temporal' | 'amygdala' | 'hippocampus' | 'cerebellum';
export const BRAIN_REGIONS: Record<RegionId, { x: number; y: number; rx: number; ry: number }> = {
  prefrontal: { x: 88, y: 125, rx: 46, ry: 58 },
  motor: { x: 190, y: 82, rx: 40, ry: 50 },
  parietal: { x: 272, y: 82, rx: 48, ry: 40 },
  occipital: { x: 332, y: 152, rx: 28, ry: 40 },
  temporal: { x: 170, y: 220, rx: 62, ry: 24 },
  amygdala: { x: 150, y: 206, rx: 12, ry: 10 },
  hippocampus: { x: 186, y: 200, rx: 26, ry: 9 },
  cerebellum: { x: 296, y: 246, rx: 36, ry: 26 },
};

/** Evenly spaced places along a polyline, by length; n of them, the first half a step in. */
export function spread(points: { x: number; y: number }[], n: number): { x: number; y: number; along: number }[] {
  if (!points.length || n <= 0) return [];
  const lengths = [0];
  for (let i = 1; i < points.length; i++) {  // a jump over a left-out part (the cerebellum) counts as no length
    const d = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
    lengths.push(lengths[i - 1] + (d > 12 ? 0 : d));
  }
  const total = lengths[lengths.length - 1];
  const out: { x: number; y: number; along: number }[] = [];
  let j = 1;
  for (let k = 0; k < n; k++) {
    const want = total * (k + .5) / n;
    while (j < points.length - 1 && lengths[j] < want) j++;
    const span = lengths[j] - lengths[j - 1] || 1, t = Math.min(1, Math.max(0, (want - lengths[j - 1]) / span));
    out.push({ x: points[j - 1].x + (points[j].x - points[j - 1].x) * t, y: points[j - 1].y + (points[j].y - points[j - 1].y) * t, along: want / (total || 1) });
  }
  return out;
}
