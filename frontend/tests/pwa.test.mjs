import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const read = (p) => readFileSync(new URL(p, import.meta.url), 'utf8');

test('the manifest makes the app installable', () => {
  const m = JSON.parse(read('../public/manifest.webmanifest'));
  assert.equal(m.display, 'standalone');
  assert.equal(m.start_url, '/');
  assert.ok(m.icons.some((i) => i.sizes === '512x512'));
  assert.match(read('../index.html'), /rel="manifest" href="\/manifest\.webmanifest"/);
});

test('the service worker never answers API calls or other origins', () => {
  const handlers = {};
  const sandbox = { self: { addEventListener: (t, f) => { handlers[t] = f; }, location: { origin: 'https://dreamlib.cenker.dev' } }, URL, caches: { match: async () => null, open: async () => ({ put() {} }) }, fetch: async () => ({ ok: false }) };
  vm.runInNewContext(read('../public/sw.js'), sandbox);
  const answered = (url, mode = 'no-cors', method = 'GET') => {
    let hit = false;
    handlers.fetch({ request: { url, mode, method }, respondWith: () => { hit = true; } });
    return hit;
  };
  assert.equal(answered('https://dreamlib.cenker.dev/api/v1/dreams'), false);
  assert.equal(answered('https://dreamlib.cenker.dev/healthz'), false);
  assert.equal(answered('https://other.example/assets/x.js'), false);
  assert.equal(answered('https://dreamlib.cenker.dev/assets/index-abc.js', 'no-cors', 'POST'), false);
  assert.equal(answered('https://dreamlib.cenker.dev/assets/index-abc.js'), true);
  assert.equal(answered('https://dreamlib.cenker.dev/library', 'navigate'), true);
});
