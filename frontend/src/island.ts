/** The library island's arithmetic: each feeling gets a district (a slice of the island), and inside it the
 * dreams lie in rings, newest nearest the centre. Pure, so the same dreams always land in the same place. */
export type IslandDream = { id: string; day: string; feeling: string };
export type IslandSpot = { id: string; x: number; z: number; district: number };
export type District = { feeling: string; from: number; to: number; count: number };

export const CARD = { width: 0.9, depth: 1.2, gap: 1.35, core: 1.7 };

export function islandLayout(dreams: IslandDream[], most = 6): { spots: IslandSpot[]; districts: District[]; radius: number } {
  const counts = new Map<string, number>();
  for (const d of dreams) counts.set(d.feeling, (counts.get(d.feeling) ?? 0) + 1);
  let feelings = [...counts.keys()].sort((a, b) => (counts.get(b)! - counts.get(a)!) || a.localeCompare(b));
  if (feelings.length > most) feelings = [...feelings.filter(f => f).slice(0, most - 1), ''];  // the rest share one quiet district
  const known = new Set(feelings);
  const groups = feelings.map(feeling => dreams.filter(d => (known.has(d.feeling) ? d.feeling : '') === feeling)
    .sort((a, b) => b.day.localeCompare(a.day) || a.id.localeCompare(b.id)));
  const whole = feelings.length <= 1;
  // a slice grows with its dreams, but even one dream gets room; then the slices are scaled into one turn
  const raw = groups.map(g => Math.max(.6, g.length));
  const sum = raw.reduce((a, b) => a + b, 0);
  const spots: IslandSpot[] = [];
  const districts: District[] = [];
  let start = -Math.PI / 2, radius = CARD.core;
  groups.forEach((group, district) => {
    const share = Math.PI * 2 * raw[district] / sum;
    districts.push({ feeling: feelings[district], from: start, to: start + share, count: group.length });
    const margin = whole ? 0 : .1;
    let placed = 0;
    for (let ring = 0; placed < group.length; ring++) {
      const r = CARD.core + ring * CARD.gap;
      const room = Math.max(1, Math.floor((share - margin * 2) * r / CARD.gap));
      const here = Math.min(room, group.length - placed);
      for (let k = 0; k < here; k++) {
        const t = whole ? start + share * (k + ring * .5) / room : start + margin + (share - margin * 2) * (k + .5) / here;
        spots.push({ id: group[placed + k].id, x: Math.cos(t) * r, z: Math.sin(t) * r, district });
      }
      placed += here;
      radius = Math.max(radius, r);
    }
    start += share;
  });
  return { spots, districts, radius: radius + CARD.depth + .55 };  // room at the rim for the feelings' names
}
