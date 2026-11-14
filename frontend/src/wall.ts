/** Masonry arithmetic for the library wall (G7); the cards stay in date order in the page. */
export const WALL_PAGE = 24;

export function wallColumns(width: number): { count: number; gap: number } {
  if (width < 560) return { count: 2, gap: 12 };
  return { count: width < 900 ? 3 : 4, gap: 20 };
}

/** Each card goes under the shortest column so far, so the wall fills evenly and new pages never move old cards. */
export function placeCards(heights: number[], count: number, columnWidth: number, gap: number) {
  const tops = new Array<number>(count).fill(0);
  const spots = heights.map(height => {
    const column = tops.indexOf(Math.min(...tops));
    const spot = { x: column * (columnWidth + gap), y: tops[column] };
    tops[column] += height + gap;
    return spot;
  });
  return { spots, height: Math.max(0, Math.max(...tops) - gap) };
}
