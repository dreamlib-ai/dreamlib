import { useEffect, useRef } from 'react';
import { NOISE, VERTEX } from './glsl';

/** The living background: light liquid ink forms folding in soft focus over deep navy, with a violet-cyan
 * fringe (from the "echoes of abstract" loop Cenker picked). The ink's light drifts slowly through four related
 * tones (ultramarine, sea glass, lilac, dusk blue), and the change runs along the ink's own shapes so it never
 * reads as a fade. One three.js shader on a fixed canvas; three.js loads after the first paint and the CSS
 * gradient on body stands in until then or without WebGL. Reduced motion draws one still frame. */
const FRAGMENT = `
precision highp float;
uniform float time;
uniform vec2 size;
varying vec2 vUv;
${NOISE}

vec3 tone(float k) {
  // four neighbouring tones of the same light, looped
  vec3 a = vec3(0.42, 0.52, 0.92);  // ultramarine
  vec3 b = vec3(0.34, 0.66, 0.82);  // sea glass
  vec3 c = vec3(0.58, 0.52, 0.92);  // lilac
  vec3 d = vec3(0.40, 0.58, 0.98);  // dusk blue
  k = fract(k) * 4.0;
  if (k < 1.0) return mix(a, b, smoothstep(0.0, 1.0, k));
  if (k < 2.0) return mix(b, c, smoothstep(1.0, 2.0, k));
  if (k < 3.0) return mix(c, d, smoothstep(2.0, 3.0, k));
  return mix(d, a, smoothstep(3.0, 4.0, k));
}

void main() {
  float aspect = size.x / size.y;
  vec2 q = vec2(vUv.x * aspect, vUv.y) * 1.15;
  float t = time * 0.045;
  vec2 w = vec2(fbm(q + vec2(t, 0.0)), fbm(q + vec2(5.2, 1.3) - vec2(0.0, t)));
  float f = fbm(q * 1.2 + w * 1.9 + vec2(t * 0.6, -t * 0.4));

  float soft = 0.02 + 0.09 * smoothstep(0.0, 1.0, vUv.y);
  float edge = 0.6;
  float r = smoothstep(edge - soft, edge + soft, f + 0.016);
  float g = smoothstep(edge - soft, edge + soft, f);
  float b = smoothstep(edge - soft, edge + soft, f - 0.02);

  // one full tone loop every ~160 s, offset by the ink itself so neighbouring forms are a step apart
  vec3 light = tone(time / 160.0 + f * 0.35 + w.x * 0.15);
  vec3 base = mix(vec3(0.012, 0.018, 0.055), vec3(0.03, 0.06, 0.17), smoothstep(0.2, 0.6, f));
  vec3 col = base + vec3(r * 0.78, g * 0.88, b) * light * 0.82;
  col += vec3(0.32, 0.18, 0.75) * clamp(b - r, 0.0, 1.0) * 0.9;
  col += vec3(0.08, 0.5, 0.6) * clamp(r - b, 0.0, 1.0) * 0.45;

  float n = hash(gl_FragCoord.xy * 0.97 + fract(time * 0.41) * 77.0);
  col = col * (0.9 + 0.2 * n) + (n - 0.5) * 0.03;
  gl_FragColor = vec4(col, 1.0);
}`;

export default function Sky() {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let stop = () => {};
    let cancelled = false;
    void import('three').then(THREE => {
      const node = host.current;
      if (cancelled || !node) return;
      let renderer: InstanceType<typeof THREE.WebGLRenderer>;
      try { renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'low-power' }); } catch { return; }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      node.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const start = Number(new URLSearchParams(window.location.search).get('skyAt')) || 0;  // preview a moment of the loop
      const uniforms = { time: { value: start }, size: { value: new THREE.Vector2(1, 1) } };
      const material = new THREE.ShaderMaterial({ uniforms, vertexShader: VERTEX, fragmentShader: FRAGMENT, depthWrite: false });
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
        uniforms.time.value = start + (now - started) / 1000;
        renderer.render(scene, camera);
      };
      if (!still) frame = requestAnimationFrame(tick);
      stop = () => { cancelAnimationFrame(frame); window.removeEventListener('resize', fit); plane.geometry.dispose(); material.dispose(); renderer.dispose(); renderer.domElement.remove(); };
    }).catch(() => {});
    return () => { cancelled = true; stop(); };
  }, []);
  return <div ref={host} className="sky" aria-hidden="true" />;
}
