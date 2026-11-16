import { useEffect, useRef } from 'react';
import type { Dream } from './api';
import { CARD, islandLayout, type District } from './island';
import { normalizeTag } from './themes';
import { tr } from './strings';

/** The library seen from above: a dark island in the night, one slice per feeling, every dream a little card
 * lying on it (its picture, or its title on paper). Drag to move, pinch or wheel to come closer, tap a card to
 * open it. Draws only when something changes, so it rests between touches. Without WebGL it calls onFail. */
const TINTS = ['#f2c4cf', '#b9a6ff', '#8fd8ff', '#c7e8c4', '#ffd8a8', '#cfd3e6'];
const dayOf = (d: Dream) => d.journal?.dreamedOn ?? d.createdAt.slice(0, 10);
export const feelingOf = (d: Dream) => {
  const top = [...d.emotions].filter(e => e.pct > 0).sort((a, b) => b.pct - a.pct)[0];
  return top ? normalizeTag(top.label) : '';
};

type View = { x: number; z: number; height: number };

export default function LibraryIsland({ dreams, onOpen, onFail }: { dreams: Dream[]; onOpen: (dream: Dream) => void; onFail: () => void }) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<View | null>(null);  // where the eye is, kept while the dreams change
  const steered = useRef(false);  // until the reader moves it, the eye keeps the whole island in view
  const open = useRef(onOpen); open.current = onOpen;
  const fail = useRef(onFail); fail.current = onFail;
  const shape = dreams.map(d => `${d.id}:${d.title}:${d.panels.find(p => p.url)?.path ?? ''}:${feelingOf(d)}`).join('|');  // rebuild only when what is drawn changes

  useEffect(() => {
    let stop = () => {};
    let cancelled = false;
    void import('three').then(THREE => {
      const node = host.current;
      if (cancelled || !node) return;
      let renderer: InstanceType<typeof THREE.WebGLRenderer>;
      try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' }); }
      catch { fail.current(); return; }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
      renderer.setClearColor(0x000000, 0);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      node.appendChild(renderer.domElement);

      const labels = new Map(dreams.flatMap(d => d.emotions.map(e => [normalizeTag(e.label), e.label] as const)));
      const { spots, districts, radius } = islandLayout(dreams.map(d => ({ id: d.id, day: dayOf(d), feeling: feelingOf(d) })));
      const byId = new Map(dreams.map(d => [d.id, d]));
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, .1, 200);
      const disposables: { dispose: () => void }[] = [];
      const keep = <T extends { dispose: () => void }>(thing: T) => { disposables.push(thing); return thing; };

      // The ground: one painted texture with the island's glow, the feeling slices and their names at the rim.
      const ground = keep(new THREE.CanvasTexture(paintGround(districts, radius, labels)));
      ground.colorSpace = THREE.SRGBColorSpace;
      ground.anisotropy = renderer.capabilities.getMaxAnisotropy();
      const land = new THREE.Mesh(keep(new THREE.PlaneGeometry(radius * 2.6, radius * 2.6)), keep(new THREE.MeshBasicMaterial({ map: ground, transparent: true, depthWrite: false })));
      land.rotation.x = -Math.PI / 2;
      scene.add(land);

      const shadowTex = keep(new THREE.CanvasTexture(paintShadow()));
      const shadowMat = keep(new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }));
      const cardGeo = keep(new THREE.PlaneGeometry(CARD.width, CARD.depth));
      const shadowGeo = keep(new THREE.PlaneGeometry(CARD.width * 1.5, CARD.depth * 1.45));
      const cards: InstanceType<typeof THREE.Mesh>[] = [];
      const loader = new THREE.TextureLoader();
      loader.setCrossOrigin('anonymous');
      for (const spot of spots) {
        const dream = byId.get(spot.id)!;
        const tint = TINTS[spot.district % TINTS.length];
        const paper = keep(new THREE.CanvasTexture(paintPaper(dream.title, tint)));
        paper.colorSpace = THREE.SRGBColorSpace;
        const material = keep(new THREE.MeshBasicMaterial({ map: paper }));
        const card = new THREE.Mesh(cardGeo, material);
        card.rotation.set(-Math.PI / 2, (hash(spot.id) - .5) * .32, 0, 'YXZ');  // upright to the eye, a little askew
        card.position.set(spot.x, .02 + hash(spot.id + 'h') * .01, spot.z);
        card.userData.id = dream.id;
        const shade = new THREE.Mesh(shadowGeo, shadowMat);
        shade.rotation.copy(card.rotation);
        shade.position.set(spot.x + .06, .005, spot.z + .1);
        scene.add(shade, card);
        cards.push(card);
        const picture = dream.panels.find(p => p.url);
        if (picture) loader.load((picture.thumb || picture.url)!, texture => {
          if (cancelled) { texture.dispose(); return; }
          texture.colorSpace = THREE.SRGBColorSpace;
          cover(texture, CARD.width / CARD.depth);
          keep(texture); material.map = texture; material.needsUpdate = true; draw();
        }, undefined, () => {});
      }

      // The eye looks down at an angle; height is the zoom.
      // First the whole island, its names at the rim included, fitted to the narrower side of the screen.
      const overview = () => radius * 1.02 / (Math.hypot(1, .62) * Math.tan(camera.fov * Math.PI / 360) * Math.min(1, camera.aspect));
      let far = radius * 2.3;
      const near = 2.4;
      const eye: View = view.current ?? { x: 0, z: 0, height: radius * 2 };
      view.current = eye;

      const place = () => {
        const reach = radius * .8;
        const d = Math.hypot(eye.x, eye.z);
        if (d > reach) { eye.x *= reach / d; eye.z *= reach / d; }
        eye.height = Math.min(far, Math.max(near, eye.height));
        camera.position.set(eye.x, eye.height, eye.z + eye.height * .62);
        camera.lookAt(eye.x, 0, eye.z);
      };
      let queued = 0;
      function draw() { if (!queued) queued = requestAnimationFrame(() => { queued = 0; place(); renderer.render(scene, camera); }); }
      const fit = () => {
        const w = node.clientWidth, h = node.clientHeight;
        if (!w || !h) return;
        renderer.setSize(w, h, false);
        camera.aspect = w / h; camera.updateProjectionMatrix();
        far = Math.max(radius * 2.3, overview());
        if (!steered.current) { eye.x = 0; eye.z = 0; eye.height = overview(); }
        draw();
      };
      fit();
      const watch = new ResizeObserver(fit); watch.observe(node);

      // Touch: one finger moves, two fingers pinch, a short still tap opens a card.
      const canvas = renderer.domElement;
      const pointers = new Map<number, { x: number; y: number }>();
      let pinch = 0, downAt = 0, moved = 0;
      const perPixel = () => 2 * eye.height * Math.tan(camera.fov * Math.PI / 360) / node.clientHeight;
      const ray = new THREE.Raycaster(), at = new THREE.Vector2();
      const down = (e: PointerEvent) => {
        steered.current = true;
        canvas.setPointerCapture(e.pointerId);
        pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (pointers.size === 1) { downAt = performance.now(); moved = 0; }
        if (pointers.size === 2) pinch = spread();
      };
      const spread = () => { const [a, b] = [...pointers.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
      const move = (e: PointerEvent) => {
        const last = pointers.get(e.pointerId);
        if (!last) return;
        const dx = e.clientX - last.x, dy = e.clientY - last.y;
        pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        moved += Math.abs(dx) + Math.abs(dy);
        if (pointers.size === 1) { const k = perPixel(); eye.x -= dx * k; eye.z -= dy * k * 1.25; }
        else if (pointers.size === 2) { const now = spread(); if (pinch) eye.height *= pinch / now; pinch = now; }
        draw();
      };
      const up = (e: PointerEvent) => {
        const was = pointers.size;
        pointers.delete(e.pointerId);
        if (pointers.size < 2) pinch = 0;
        if (was === 1 && moved < 8 && performance.now() - downAt < 450) {
          const box = canvas.getBoundingClientRect();
          at.set((e.clientX - box.left) / box.width * 2 - 1, -((e.clientY - box.top) / box.height) * 2 + 1);
          ray.setFromCamera(at, camera);
          const hit = ray.intersectObjects(cards)[0];
          const dream = hit && byId.get(hit.object.userData.id);
          if (dream) open.current(dream);
        }
      };
      const wheel = (e: WheelEvent) => { e.preventDefault(); steered.current = true; eye.height *= Math.exp(e.deltaY * .0015); draw(); };
      canvas.addEventListener('pointerdown', down);
      canvas.addEventListener('pointermove', move);
      canvas.addEventListener('pointerup', up);
      canvas.addEventListener('pointercancel', up);
      canvas.addEventListener('wheel', wheel, { passive: false });
      node.classList.add('on');

      stop = () => {
        cancelAnimationFrame(queued); watch.disconnect();
        canvas.removeEventListener('pointerdown', down); canvas.removeEventListener('pointermove', move);
        canvas.removeEventListener('pointerup', up); canvas.removeEventListener('pointercancel', up); canvas.removeEventListener('wheel', wheel);
        for (const thing of disposables) thing.dispose();
        renderer.dispose(); canvas.remove(); node.classList.remove('on');
      };
    }).catch(() => fail.current());
    return () => { cancelled = true; stop(); };
  }, [shape]);

  return <>
    <div ref={host} className="island" aria-hidden="true" />
    <ul className="sr-only">{dreams.map(d => <li key={d.id}><button onClick={() => onOpen(d)}>{d.title}</button></li>)}</ul>
  </>;
}

/** A stable number in [0, 1) for one id, so a card's small tilt never changes between visits. */
function hash(text: string) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return ((h >>> 0) % 10000) / 10000;
}

/** Crop a picture to the card's shape, like object-fit: cover. */
function cover(texture: { image: { width: number; height: number }; repeat: { set: (x: number, y: number) => void }; offset: { set: (x: number, y: number) => void } }, aspect: number) {
  const { width, height } = texture.image;
  const own = width / height;
  if (own > aspect) { const k = aspect / own; texture.repeat.set(k, 1); texture.offset.set((1 - k) / 2, 0); }
  else { const k = own / aspect; texture.repeat.set(1, k); texture.offset.set(0, (1 - k) / 2); }
}

function paintPaper(title: string, tint: string) {
  const c = document.createElement('canvas'); c.width = 180; c.height = 240;
  const g = c.getContext('2d')!;
  const fill = g.createLinearGradient(0, 0, 180, 240);
  fill.addColorStop(0, '#f7f1f5'); fill.addColorStop(1, tint);
  g.fillStyle = fill; g.fillRect(0, 0, 180, 240);
  g.fillStyle = '#2a2350'; g.font = 'italic 500 22px Fraunces, Georgia, serif'; g.textBaseline = 'top';
  const words = title.split(/\s+/); let line = '', y = 22;
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (g.measureText(next).width > 148 && line) { g.fillText(line, 16, y); y += 28; line = word; if (y > 190) { line += '…'; break; } }
    else line = next;
  }
  if (line && y <= 218) g.fillText(line, 16, y);
  return c;
}

function paintShadow() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const fill = g.createRadialGradient(32, 32, 4, 32, 32, 32);
  fill.addColorStop(0, '#02041499'); fill.addColorStop(1, '#02041400');
  g.fillStyle = fill; g.fillRect(0, 0, 64, 64);
  return c;
}

/** The island: a deep glow fading into the night, faint slices for the feelings, their names along the rim. */
function paintGround(districts: District[], radius: number, labels: Map<string, string>) {
  const size = 1400, c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d')!;
  const mid = size / 2, unit = size / (radius * 2.6), r = radius * unit;
  const glow = g.createRadialGradient(mid, mid, 0, mid, mid, r * 1.12);
  glow.addColorStop(0, '#1b2a6bb3'); glow.addColorStop(.5, '#16235c88'); glow.addColorStop(.85, '#0f1a4a33'); glow.addColorStop(1, '#0a123800');
  g.fillStyle = glow; g.beginPath(); g.arc(mid, mid, r * 1.12, 0, Math.PI * 2); g.fill();
  districts.forEach((d, i) => {
    if (districts.length > 1) {
      g.fillStyle = TINTS[i % TINTS.length] + '14';
      g.beginPath(); g.moveTo(mid, mid); g.arc(mid, mid, r, d.from, d.to); g.closePath(); g.fill();
    }
    const name = d.feeling ? labels.get(d.feeling) ?? d.feeling : tr.library.otherFeelings;
    const a = (d.from + d.to) / 2, rr = r - unit * .5, px = Math.round(Math.min(64, Math.max(28, unit * .36)));
    g.save(); g.translate(mid + Math.cos(a) * rr, mid + Math.sin(a) * rr);
    g.fillStyle = TINTS[i % TINTS.length]; g.font = `italic 500 ${px}px Fraunces, Georgia, serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(name.toLocaleLowerCase('tr-TR'), 0, 0); g.restore();
  });
  return c;
}
