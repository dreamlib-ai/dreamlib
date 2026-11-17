/** The dream shelf's arithmetic: how a case leans by how far it is from the middle of the screen.
 * At the middle it faces the reader flat; further away it tips back until mostly its title band shows. */
export const SHELF = { step: 150, height: 236, lean: 70 };

/** offset: the case's centre minus the screen's centre, in pixels; half: half the screen height. */
export function shelfPose(offset: number, half: number) {
  const d = Math.max(-1.6, Math.min(1.6, offset / Math.max(half, 1)));
  const away = Math.abs(d);
  const ease = Math.min(1, away / .55);  // the middle third eases in, past it the case is fully tipped
  return {
    angle: -Math.sign(d) * SHELF.lean * (1 - Math.pow(1 - ease, 2)),
    depth: -Math.min(away, 1.2) * 140,
    fade: Math.max(0, Math.min(1, 1.45 - away * .7)),
    layer: Math.round(1000 - away * 400),
    front: away < .2,
    below: Math.max(0, Math.min(1, (d - .2) / .3)),  // below the middle the title shows on the case's lower edge
  };
}
