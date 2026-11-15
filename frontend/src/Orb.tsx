import { useEffect, useRef } from 'react';
import { NOISE, VERTEX } from './glsl';

/** The microphone's moving sphere, like a voice assistant's: white clouds flow and fold inside a cobalt-to-sky
 * sphere with a pink blush, lit from the top left. It flows faster and brighter with --level (0..1), which
 * VoiceInput writes on the orb button. The painted cloud layer under it shows until WebGL is ready. */
const FRAGMENT = `
precision highp float;
uniform float time;
uniform float level;
varying vec2 vUv;
${NOISE}
void main() {
  vec2 p = vUv * 2.0 - 1.0;
  float r = length(p);
  float edge = smoothstep(1.0, 0.975, r);
  if (edge <= 0.0) { gl_FragColor = vec4(0.0); return; }
  float z = sqrt(max(0.0, 1.0 - r * r));
  vec2 s = p / (0.6 + z * 0.4);
  float t = time * (0.16 + level * 0.5);
  float a = fbm(s * 0.9 + vec2(t, -t * 0.6));
  float b = fbm(s * 1.3 + vec2(a * 2.0 - t * 0.7, a * 1.5 + t * 0.4));
  float clouds = smoothstep(0.34, 0.86, b + level * 0.08);
  vec3 deep = vec3(0.12, 0.25, 0.95);
  vec3 sky = vec3(0.47, 0.70, 1.0);
  vec3 white = vec3(0.98, 0.98, 1.0);
  vec3 pink = vec3(1.0, 0.70, 0.88);
  vec3 col = mix(deep, sky, smoothstep(-0.9, 0.9, p.y + a * 0.4));
  col = mix(col, white, clouds * 0.92);
  col = mix(col, pink, smoothstep(0.1, 1.0, dot(p, vec2(0.55, -0.83))) * 0.5 * (0.4 + clouds));
  vec3 n = vec3(p, z);
  col += pow(max(dot(n, normalize(vec3(-0.45, 0.55, 0.7))), 0.0), 18.0) * 0.35;
  col *= 0.8 + 0.2 * z;
  col += (hash(gl_FragCoord.xy + fract(time) * 50.0) - 0.5) * 0.05;
  gl_FragColor = vec4(col * edge, edge);
}`;

export default function Orb() {
  const host = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    let stop = () => {};
    let cancelled = false;
    void import('three').then(THREE => {
      const node = host.current;
      if (cancelled || !node) return;
      let renderer: InstanceType<typeof THREE.WebGLRenderer>;
      try { renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, premultipliedAlpha: true }); } catch { return; }
      const side = node.clientWidth || 168;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(side, side, false);
      node.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      const uniforms = { time: { value: 3 }, level: { value: 0 } };
      const material = new THREE.ShaderMaterial({ uniforms, vertexShader: VERTEX, fragmentShader: FRAGMENT, transparent: true, depthWrite: false });
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
      scene.add(plane);
      renderer.render(scene, camera);
      node.classList.add('on');
      const button = node.closest('.orb') as HTMLElement | null;
      const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      let frame = 0, clock = 3, last = performance.now();
      const tick = (now: number) => {
        frame = requestAnimationFrame(tick);
        if (document.hidden) { last = now; return; }
        const level = Number(button?.style.getPropertyValue('--level') || 0);
        uniforms.level.value += (level - uniforms.level.value) * 0.15;
        clock += Math.min(0.05, (now - last) / 1000) * (1 + uniforms.level.value * 2.5);
        last = now;
        uniforms.time.value = clock;
        renderer.render(scene, camera);
      };
      if (!still) frame = requestAnimationFrame(tick);
      stop = () => { cancelAnimationFrame(frame); plane.geometry.dispose(); material.dispose(); renderer.dispose(); renderer.domElement.remove(); };
    }).catch(() => {});
    return () => { cancelled = true; stop(); };
  }, []);
  return <span ref={host} className="orb-gl" aria-hidden="true" />;
}
