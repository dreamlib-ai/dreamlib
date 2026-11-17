/** Where dreams sit on the brain engraving, and the regions that can later be brought into focus. */
export type Spot = { x: number; y: number };

/** n places spread over the ridges: each next place is the one farthest from those already taken, starting at the
 * front of the brain; then ordered front to back so dreams can follow time. More dreams than ridges share them,
 * a little apart. Pure and deterministic. */
export function pickRidges(ridges: readonly number[], n: number): Spot[] {
  const all: Spot[] = [];
  for (let i = 0; i + 1 < ridges.length; i += 2) all.push({ x: ridges[i], y: ridges[i + 1] });
  if (!all.length || n <= 0) return [];
  const take = Math.min(n, all.length);
  const chosen: Spot[] = [all[0]];
  const gap = all.map(p => Math.hypot(p.x - all[0].x, p.y - all[0].y));
  while (chosen.length < take) {
    let best = 0;
    for (let i = 1; i < all.length; i++) if (gap[i] > gap[best]) best = i;
    chosen.push(all[best]);
    for (let i = 0; i < all.length; i++) gap[i] = Math.min(gap[i], Math.hypot(all[i].x - all[best].x, all[i].y - all[best].y));
  }
  chosen.sort((a, b) => a.x - b.x || a.y - b.y);
  const out = [...chosen];
  for (let k = take; k < n; k++) {  // a crowded brain: later dreams circle the same ridges
    const base = chosen[k % take], turn = Math.floor(k / take);
    out.push({ x: base.x + Math.cos(turn * 2.4) * 11 * Math.sqrt(turn), y: base.y + Math.sin(turn * 2.4) * 11 * Math.sqrt(turn) });
  }
  return out;
}

/** Regions to mark later (Cenker will place them), as soft ellipses in image pixels. When some are chosen,
 * everything else goes out of focus. Rough places for now. */
export type RegionId = 'prefrontal' | 'motor' | 'parietal' | 'occipital' | 'temporal' | 'amygdala' | 'hippocampus' | 'cerebellum';
export const BRAIN_REGIONS: Record<RegionId, { x: number; y: number; rx: number; ry: number }> = {
  prefrontal: { x: 250, y: 330, rx: 150, ry: 170 },
  motor: { x: 560, y: 190, rx: 110, ry: 130 },
  parietal: { x: 800, y: 210, rx: 140, ry: 120 },
  occipital: { x: 1020, y: 420, rx: 90, ry: 140 },
  temporal: { x: 640, y: 530, rx: 230, ry: 80 },
  amygdala: { x: 470, y: 560, rx: 40, ry: 34 },
  hippocampus: { x: 580, y: 575, rx: 80, ry: 30 },
  cerebellum: { x: 850, y: 700, rx: 150, ry: 90 },
};
