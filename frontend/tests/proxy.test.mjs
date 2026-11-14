import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker from '../worker.mjs';

const env = { API_ORIGIN: 'https://api.example.test', ASSETS: { fetch: async () => new Response('asset') } };
test('proxy forwards audio and bearer auth to the fixed origin, drops cookies and never caches API responses', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async request => {
    assert.equal(request.url, 'https://api.example.test/api/transcribe?lang=tr');
    assert.equal(request.headers.get('Authorization'), 'Bearer test-token');
    assert.equal(request.headers.get('Cookie'), null);
    assert.equal(request.headers.get('Host'), null);
    assert.equal(await request.text(), 'audio-bytes');
    return Response.json({ text: 'a dream' }, { status: 201 });
  };
  try {
    const response = await worker.fetch(new Request('https://dreamlib.cenker.dev/api/transcribe?lang=tr', { method: 'POST', body: 'audio-bytes', headers: { Authorization: 'Bearer test-token', Cookie: 'private-cookie', Host: 'dreamlib.cenker.dev' } }), env);
    assert.equal(response.status, 201);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.deepEqual(await response.json(), { text: 'a dream' });
  } finally { globalThis.fetch = original; }
});
test('asset requests use the static binding', async () => {
  assert.equal(await (await worker.fetch(new Request('https://dreamlib.cenker.dev/'), env)).text(), 'asset');
});
test('network failures produce a recoverable JSON error', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('internal address'); };
  try {
    const response = await worker.fetch(new Request('https://dreamlib.cenker.dev/healthz'), env);
    assert.equal(response.status, 502);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.ok(!(await response.text()).includes('internal address'));
  } finally { globalThis.fetch = original; }
});

test('a shared magazine page carries link-preview tags with an escaped title', async () => {
  const original = globalThis.fetch;
  const html = '<html><head><title>Dreamlib</title></head><body></body></html>';
  const assets = { fetch: async request => { assert.equal(new URL(request.url).pathname, '/'); return new Response(html); } };
  globalThis.fetch = async request => {
    assert.equal(String(request.url ?? request), 'https://api.example.test/api/v1/m/abcDEF123_-x');
    return Response.json({ spec: { cover: { title: 'Ev <ve> "deniz"' } } });
  };
  try {
    const response = await worker.fetch(new Request('https://dreamlib.cenker.dev/m/abcDEF123_-x'), { ...env, ASSETS: assets });
    const body = await response.text();
    assert.equal(response.status, 200);
    assert.match(body, /<meta property="og:title" content="Ev &lt;ve&gt; &quot;deniz&quot;" \/>/);
    assert.match(body, /og:image" content="https:\/\/dreamlib.cenker.dev\/api\/v1\/m\/abcDEF123_-x\/cover"/);
    assert.match(body, /<title>Ev &lt;ve&gt; &quot;deniz&quot; · Dreamlib<\/title>/);
  } finally { globalThis.fetch = original; }
});
test('an unknown or closed share is still the app, with no preview tags', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ error: 'yok' }, { status: 404 });
  const assets = { fetch: async () => new Response('<html><head><title>Dreamlib</title></head></html>') };
  try {
    const body = await (await worker.fetch(new Request('https://dreamlib.cenker.dev/m/abcDEF123_-x'), { ...env, ASSETS: assets })).text();
    assert.ok(!body.includes('og:title') && body.includes('noindex') && body.includes('<title>Dreamlib</title>'));
  } finally { globalThis.fetch = original; }
});

test('shared magazine pictures keep their public cache time; private answers never do', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response('png', { headers: { 'Cache-Control': 'public, max-age=3600' } });
  try {
    const picture = await worker.fetch(new Request('https://dreamlib.cenker.dev/api/v1/m/abcDEF123_-x/p/0'), env);
    assert.equal(picture.headers.get('Cache-Control'), 'public, max-age=3600');
    const mine = await worker.fetch(new Request('https://dreamlib.cenker.dev/api/v1/dreams'), env);
    assert.equal(mine.headers.get('Cache-Control'), 'no-store');
  } finally { globalThis.fetch = original; }
});
