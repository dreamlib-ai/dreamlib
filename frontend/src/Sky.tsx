import { useEffect, useRef } from 'react';

/** The living background: a slow lava lamp of pink, lilac and peach light over a deep indigo-to-plum dusk,
 * drawn by one three.js shader on a fixed canvas. three.js loads after the first paint; until then (and when
 * WebGL is missing) the CSS gradient on body shows. Reduced motion draws a single still frame. */
const FRAGMENT = `
precision highp float;
uniform float time;
uniform vec2 size;
varying vec2 vUv;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void main() {
  vec2 uv = vUv;
  float aspect = size.x / size.y;
  vec2 p = vec2(uv.x * aspect, uv.y);
  vec3 top = vec3(0.075, 0.051, 0.188);
  vec3 bottom = vec3(0.196, 0.078, 0.259);
  vec3 col = mix(bottom, top, smoothstep(0.0, 1.0, uv.y));

  vec3 tint[5];
  tint[0] = vec3(0.95, 0.56, 0.76);
  tint[1] = vec3(0.70, 0.60, 0.96);
  tint[2] = vec3(0.98, 0.76, 0.58);
  tint[3] = vec3(0.89, 0.45, 0.66);
  tint[4] = vec3(0.52, 0.50, 0.93);
  float field = 0.0;
  vec3 glow = vec3(0.0);
  for (int i = 0; i < 5; i++) {
    float f = float(i);
    float t = time * (0.045 + f * 0.009);
    vec2 c = vec2(aspect * (0.5 + 0.42 * sin(t * 1.3 + f * 1.9)), 0.5 + 0.44 * cos(t + f * 2.6));
    float r = 0.16 + 0.05 * sin(t * 2.0 + f);
    float d = length(p - c);
    float w = (r * r) / (d * d + 0.002);
    field += w;
    glow += tint[i] * w;
  }
  vec3 blob = glow / max(field, 0.0001);
  float lava = smoothstep(0.75, 1.8, field);
  float halo = smoothstep(0.12, 0.9, field);
  col = mix(col, blob * 0.62, lava * 0.8);
  col += blob * halo * 0.12;
  vec2 v = uv - 0.5;
  col *= 1.0 - dot(v, v) * 0.55;
  col += (hash(gl_FragCoord.xy + fract(time)) - 0.5) * 0.035;
  gl_FragColor = vec4(col, 1.0);
}`;
const VERTEX = 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';

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
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25));
      node.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const uniforms = { time: { value: 40 }, size: { value: new THREE.Vector2(1, 1) } };
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
        if (!document.hidden) { uniforms.time.value = 40 + (now - started) / 1000; renderer.render(scene, camera); }
        frame = requestAnimationFrame(tick);
      };
      if (!still) frame = requestAnimationFrame(tick);
      stop = () => { cancelAnimationFrame(frame); window.removeEventListener('resize', fit); plane.geometry.dispose(); material.dispose(); renderer.dispose(); renderer.domElement.remove(); };
    }).catch(() => {});
    return () => { cancelled = true; stop(); };
  }, []);
  return <div ref={host} className="sky" aria-hidden="true" />;
}
