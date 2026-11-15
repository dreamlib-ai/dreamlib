import { useEffect, useRef } from 'react';
import { NOISE, VERTEX } from './glsl';

/** The living background, after the risograph posters on Cenker's Pinterest: a grainy cobalt-to-violet smoke
 * rising from the bottom of a night-ink page, a faint pink spray from the top corner, all seen through fluted
 * glass (thin vertical ribs). One three.js shader on a fixed canvas; three.js loads after the first paint and
 * the CSS gradient on body stands in until then or without WebGL. Reduced motion draws one still frame. */
const FRAGMENT = `
precision highp float;
uniform float time;
uniform vec2 size;
varying vec2 vUv;
${NOISE}
void main() {
  vec2 uv = vUv;
  float rib = sin(uv.x * size.x / 18.0 * 6.2831);
  vec2 g = uv + vec2(rib * 0.005, 0.0);
  float aspect = size.x / size.y;
  vec2 q = vec2(g.x * aspect, g.y);
  float t = time * 0.035;
  float warp = fbm(q * 1.6 + vec2(0.0, -t * 2.0));
  float smoke = fbm(vec2(q.x * 1.8 + warp * 0.9, q.y * 1.3 - t * 3.0));
  float sway = 0.5 + 0.12 * sin(time * 0.04);
  float column = 1.0 - smoothstep(0.0, 0.62, abs(g.x - sway) * 1.25);
  float rise = smoothstep(0.92, -0.05, g.y + (smoke - 0.5) * 0.55);
  float plume = clamp(rise * (0.45 + 0.75 * column) * (0.55 + smoke * 0.9), 0.0, 1.0);
  float spray = smoothstep(0.75, 0.0, length((g - vec2(0.95, 1.02)) * vec2(aspect * 0.8, 1.0))) * (0.5 + 0.6 * fbm(q * 2.4 + t));

  vec3 ink = vec3(0.027, 0.031, 0.094);
  vec3 cobalt = vec3(0.13, 0.22, 0.92);
  vec3 violet = vec3(0.47, 0.34, 0.98);
  vec3 pink = vec3(1.0, 0.64, 0.86);
  vec3 col = ink;
  col = mix(col, cobalt, plume * 0.95);
  col = mix(col, violet, smoothstep(0.38, 0.85, plume) * 0.75);
  col = mix(col, pink, smoothstep(0.72, 1.0, plume) * 0.5);
  col = mix(col, pink * 0.75, spray * 0.32);
  col += rib * 0.012 * (0.4 + plume);
  float grain = hash(gl_FragCoord.xy * 0.93 + fract(time * 0.37) * 91.0);
  col *= 0.86 + 0.28 * grain;
  col += (grain - 0.5) * 0.04;
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
      const uniforms = { time: { value: 60 }, size: { value: new THREE.Vector2(1, 1) } };
      const material = new THREE.ShaderMaterial({ uniforms, vertexShader: VERTEX, fragmentShader: FRAGMENT, depthWrite: false });
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
      scene.add(plane);
      const fit = () => { renderer.setSize(window.innerWidth, window.innerHeight, false); uniforms.size.value.set(window.innerWidth, window.innerHeight); renderer.render(scene, camera); };
      fit();
      window.addEventListener('resize', fit);
      node.classList.add('on');
      const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const started = performance.now();
      let frame = 0, last = 0;
      const tick = (now: number) => {
        frame = requestAnimationFrame(tick);
        if (document.hidden || now - last < 33) return;  // ~30 fps is plenty for slow smoke
        last = now;
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
