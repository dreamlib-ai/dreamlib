import { useEffect, useRef, useState } from 'react';
import wave from './assets/koala/wave.webp';

/** Opening, after tokonomy's: soft dream dust drifts in from every side and gathers into the koala's outline,
 * holds for a beat and lifts away, sparkles only (no picture), then the overlay clears and the page settles in (html.arriving).
 * Once per session; a tap, key or scroll skips it; reduced motion skips it entirely. */
const KEY = 'dreamlib:intro-seen';
const COLORS = ['#ffd0ea', '#b9a6ff', '#8fb0ff', '#ffffff'];
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const ease = (k: number) => 1 - Math.pow(1 - k, 3);
const settle = (k: number) => 1 + 2.1 * Math.pow(k - 1, 3) + 1.1 * Math.pow(k - 1, 2);

function seen() { try { return sessionStorage.getItem(KEY) === '1'; } catch { return false; } }

export default function Intro() {
  const [on] = useState(() => !seen() && !window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [gone, setGone] = useState(!on);
  useEffect(() => {
    if (!on) return;
    try { sessionStorage.setItem(KEY, '1'); } catch { /* private mode: the intro may show again */ }
    const root = document.documentElement;
    root.classList.add('intro');
    const layer = canvas.current!;
    const ink = layer.getContext('2d')!;
    const W = window.innerWidth, H = window.innerHeight, scale = Math.min(window.devicePixelRatio || 1, 2);
    layer.width = W * scale; layer.height = H * scale;
    ink.setTransform(scale, 0, 0, scale, 0, 0);
    let frame = 0, alive = true;
    const art = new Image(); art.src = wave;
    const finish = () => {
      if (!alive) return; alive = false;
      root.classList.remove('intro'); root.classList.add('arriving');
      setTimeout(() => root.classList.remove('arriving'), 1800);
      setGone(true);
    };
    const begin = () => {
      const side = Math.min(W * .62, H * .42, 340);
      const ox = (W - side) / 2, oy = (H - side) / 2 - H * .04;
      const dots: { tx: number; ty: number; sx: number; sy: number; r: number; c: string; delay: number; seed: number }[] = [];
      try {
        const N = 90, grid = document.createElement('canvas'); grid.width = grid.height = N;
        const g = grid.getContext('2d', { willReadFrequently: true })!; g.drawImage(art, 0, 0, N, N);
        const a = g.getImageData(0, 0, N, N).data;
        const solid = (x: number, y: number) => x >= 0 && y >= 0 && x < N && y < N && a[4 * (y * N + x) + 3] > 110;
        for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
          if (!solid(x, y)) continue;
          const edge = [1, 2].some(k => !solid(x - k, y) || !solid(x + k, y) || !solid(x, y - k) || !solid(x, y + k));
          if (!edge && Math.random() > .06) continue;
          dots.push({ tx: ox + (x + .5) * side / N, ty: oy + (y + .5) * side / N, sx: 0, sy: 0, r: edge ? 1.6 + Math.random() * 1.6 : 1 + Math.random(), c: COLORS[(x * 7 + y * 3) % COLORS.length], delay: Math.random() * .6, seed: Math.random() * 6.28 });
        }
      } catch { /* image unreadable: the overlay just fades */ }
      const far = Math.hypot(W, H) * .62;
      for (const d of dots) { const t = Math.random() * Math.PI * 2, r = far * (.7 + Math.random() * .5); d.sx = W / 2 + Math.cos(t) * r; d.sy = H / 2 + Math.sin(t) * r; }
      const GATHER = 1.5, SHOW = 1.9, CLEAR = 2.6, END = 3.3;
      let start = performance.now();
      const skip = () => { start = Math.min(start, performance.now() - CLEAR * 1000); };
      window.addEventListener('pointerdown', skip, { once: true });
      window.addEventListener('keydown', skip, { once: true });
      window.addEventListener('wheel', skip, { once: true, passive: true });
      const draw = (now: number) => {
        const t = (now - start) / 1000;
        ink.clearRect(0, 0, W, H);
        const fade = ease(clamp((t - CLEAR) / (END - CLEAR), 0, 1));
        layer.style.opacity = String(1 - fade);
        if (t > CLEAR && alive) finish();
        ink.globalCompositeOperation = 'lighter';
        for (const d of dots) {
          const k = clamp((t - d.delay) / (GATHER - .5), 0, 1);
          if (k <= 0) continue;
          const m = settle(k), wob = 1.6;
          // Once the koala has formed it holds for a beat, then the sparkles lift away like breath.
          const lift = Math.pow(clamp((t - SHOW) / (END - SHOW), 0, 1), 1.6);
          const x = d.sx + (d.tx - d.sx) * m + Math.sin(t * 1.6 + d.seed) * wob + Math.sin(d.seed * 3) * lift * 40;
          const y = d.sy + (d.ty - d.sy) * m + Math.cos(t * 1.2 + d.seed * 1.7) * wob - lift * (60 + d.seed * 22);
          const twinkle = .6 + .4 * Math.sin(t * 5 + d.seed * 3);
          const glow = t > GATHER - .2 && t < SHOW + .5 ? 1.25 : 1;
          ink.globalAlpha = Math.min(1, Math.min(1, k * 2.5) * twinkle * glow * (1 - lift * .6));
          ink.fillStyle = d.c;
          ink.beginPath(); ink.arc(x, y, d.r, 0, Math.PI * 2); ink.fill();
          ink.globalAlpha *= .22; ink.beginPath(); ink.arc(x, y, d.r * 2.4, 0, Math.PI * 2); ink.fill();
        }
        ink.globalCompositeOperation = 'source-over';
        if (t < END) frame = requestAnimationFrame(draw);
      };
      frame = requestAnimationFrame(draw);
    };
    if (art.complete) begin(); else { art.onload = begin; art.onerror = finish; }
    const safety = setTimeout(finish, 6000);
    return () => { cancelAnimationFrame(frame); clearTimeout(safety); root.classList.remove('intro'); };
  }, [on]);
  return gone ? null : <canvas ref={canvas} className="intro-layer" aria-hidden="true" />;
}
