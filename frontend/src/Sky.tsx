import { useEffect, useRef } from 'react';
import { NOISE, VERTEX } from './glsl';

/** The living background, three takes from Cenker's references, each a slow real-world texture in one three.js
 * shader on a fixed canvas:
 *  - ink:   liquid ink forms folding in soft focus, with a violet-cyan fringe (the "echoes of abstract" loop)
 *  - water: night water caustics, cyan light lines rippling over deep navy (the painted pool)
 *  - riso:  cobalt spray-paint stipple drifting like clouds (the risograph prints)
 * Picked with ?sky=ink|water|riso (kept in localStorage) until one is chosen. three.js loads after first paint;
 * the CSS gradient on body stands in until then or without WebGL. Reduced motion draws one still frame. */
export type SkyKind = 'ink' | 'water' | 'riso';
const KINDS: SkyKind[] = ['ink', 'water', 'riso'];

export function skyKind(): SkyKind {
  const asked = new URLSearchParams(window.location.search).get('sky') as SkyKind | null;
  try {
    if (asked && KINDS.includes(asked)) { localStorage.setItem('dreamlib:sky', asked); return asked; }
    const kept = localStorage.getItem('dreamlib:sky') as SkyKind | null;
    if (kept && KINDS.includes(kept)) return kept;
  } catch { /* storage blocked */ }
  return 'ink';
}

/** Button skins to compare, picked with ?button=… (kept in localStorage) until one is chosen. */
export type ButtonSkin = 'cloud' | 'riso' | 'light' | 'ink' | 'ice';
export const BUTTON_SKINS: ButtonSkin[] = ['cloud', 'riso', 'light', 'ink', 'ice'];
export function buttonSkin(): ButtonSkin {
  const asked = new URLSearchParams(window.location.search).get('button') as ButtonSkin | null;
  try {
    if (asked && BUTTON_SKINS.includes(asked)) { localStorage.setItem('dreamlib:button', asked); return asked; }
    const kept = localStorage.getItem('dreamlib:button') as ButtonSkin | null;
    if (kept && BUTTON_SKINS.includes(kept)) return kept;
  } catch { /* storage blocked */ }
  return 'cloud';
}

const HEAD = `
precision highp float;
uniform float time;
uniform vec2 size;
varying vec2 vUv;
${NOISE}
vec3 finish(vec3 col) {
  float g = hash(gl_FragCoord.xy * 0.97 + fract(time * 0.41) * 77.0);
  return col * (0.9 + 0.2 * g) + (g - 0.5) * 0.03;
}`;

const BODY: Record<SkyKind, string> = {
  ink: `
void main() {
  float aspect = size.x / size.y;
  vec2 q = vec2(vUv.x * aspect, vUv.y) * 1.15;
  float t = time * 0.045;
  vec2 w = vec2(fbm(q + vec2(t, 0.0)), fbm(q + vec2(5.2, 1.3) - vec2(0.0, t)));
  float f = fbm(q * 1.2 + w * 1.9 + vec2(t * 0.6, -t * 0.4));
  float soft = 0.02 + 0.09 * smoothstep(0.0, 1.0, vUv.y);
  float edge = 0.62;
  float r = smoothstep(edge - soft, edge + soft, f + 0.016);
  float g = smoothstep(edge - soft, edge + soft, f);
  float b = smoothstep(edge - soft, edge + soft, f - 0.02);
  vec3 ink = mix(vec3(0.012, 0.018, 0.055), vec3(0.03, 0.06, 0.17), smoothstep(0.2, 0.6, f));
  vec3 light = vec3(0.42, 0.52, 0.86);
  vec3 col = ink + vec3(r * 0.7, g * 0.82, b) * light * 0.55;
  col += vec3(0.32, 0.18, 0.75) * clamp(b - r, 0.0, 1.0) * 0.9;
  col += vec3(0.08, 0.5, 0.6) * clamp(r - b, 0.0, 1.0) * 0.45;
  gl_FragColor = vec4(finish(col), 1.0);
}`,
  water: `
void main() {
  float aspect = size.x / size.y;
  vec2 uv = vec2(vUv.x * aspect, vUv.y);
  float t = time * 0.22 + 23.0;
  vec2 p = mod(uv * 9.0 + vec2(0.0, time * 0.01), 6.2831) - 250.0;
  vec2 i = p;
  float c = 1.0;
  for (int n = 0; n < 5; n++) {
    float tn = t * (1.0 - (3.5 / float(n + 1)));
    i = p + vec2(cos(tn - i.x) + sin(tn + i.y), sin(tn - i.y) + cos(tn + i.x));
    c += 1.0 / length(vec2(p.x / (sin(i.x + tn) / 0.005), p.y / (cos(i.y + tn) / 0.005)));
  }
  c /= 5.0;
  c = 1.17 - pow(c, 1.4);
  float lines = clamp(pow(abs(c), 9.0) * 1.3, 0.0, 1.0);
  float depth = 0.55 + 0.45 * fbm(uv * 1.5 + time * 0.02);
  vec3 navy = mix(vec3(0.01, 0.02, 0.06), vec3(0.03, 0.07, 0.2), depth);
  vec3 cyan = mix(vec3(0.1, 0.45, 0.95), vec3(0.35, 0.95, 0.9), fbm(uv * 3.0 - time * 0.03));
  vec3 col = navy + cyan * lines * 0.75 * depth;
  gl_FragColor = vec4(finish(col), 1.0);
}`,
  riso: `
void main() {
  float aspect = size.x / size.y;
  vec2 q = vec2(vUv.x * aspect, vUv.y);
  float t = time * 0.02;
  float f = fbm(q * 1.4 + vec2(t, t * 0.4) + fbm(q * 0.8 - t) * 0.8);
  float density = smoothstep(0.28, 0.8, f) * (0.35 + 0.65 * (1.0 - vUv.y * 0.6));
  float speck = step(grain(floor(gl_FragCoord.xy / 1.5)), density);
  vec3 col = mix(vec3(0.02, 0.025, 0.07), vec3(0.11, 0.17, 0.98), speck * 0.9);
  col += vec3(0.0, 0.02, 0.12) * density;
  gl_FragColor = vec4(finish(col), 1.0);
}`,
};

export default function Sky() {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let stop = () => {};
    let cancelled = false;
    const kind = skyKind();
    document.documentElement.dataset.sky = kind;
    void import('three').then(THREE => {
      const node = host.current;
      if (cancelled || !node) return;
      let renderer: InstanceType<typeof THREE.WebGLRenderer>;
      try { renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'low-power' }); } catch { return; }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, kind === 'riso' ? 2 : 1.5));
      node.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const uniforms = { time: { value: 60 }, size: { value: new THREE.Vector2(1, 1) } };
      const material = new THREE.ShaderMaterial({ uniforms, vertexShader: VERTEX, fragmentShader: HEAD + BODY[kind], depthWrite: false });
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
      scene.add(plane);
      const fit = () => { renderer.setSize(window.innerWidth, window.innerHeight, false); uniforms.size.value.set(window.innerWidth, window.innerHeight); renderer.render(scene, camera); };
      fit();
      window.addEventListener('resize', fit);
      node.classList.add('on');
      const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const started = performance.now();
      let frame = 0;
      const tick = (now: number) => {
        frame = requestAnimationFrame(tick);
        if (document.hidden) return;
        uniforms.time.value = 60 + (now - started) / 1000;
        renderer.render(scene, camera);
      };
      if (!still) frame = requestAnimationFrame(tick);
      stop = () => { cancelAnimationFrame(frame); window.removeEventListener('resize', fit); plane.geometry.dispose(); material.dispose(); renderer.dispose(); renderer.domElement.remove(); };
    }).catch(() => {});
    return () => { cancelled = true; stop(); };
  }, []);
  return <div ref={host} className="sky" aria-hidden="true" />;
}
