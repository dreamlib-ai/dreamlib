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
