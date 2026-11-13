import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, createContext } from 'node:vm';

async function setup({ permission, supported = ['audio/webm;codecs=opus'], missing = false } = {}) {
  const events = { states: [], errors: [], audio: [] };
  const track = { stopped: false, onended: null, stop() { this.stopped = true; } };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  const timers = new Map(), queued = [], captures = [];
  let requests = 0;
  class Capture {
    static isTypeSupported(type) { return supported.includes(type); }
    constructor(_stream, options) { this.mimeType = options?.mimeType || 'audio/webm'; this.state = 'inactive'; captures.push(this); }
    start() { this.state = 'recording'; }
    data(value = new Blob(['voice'])) { this.ondataavailable?.({ data: value }); }
    stop() { this.state = 'inactive'; queued.push(() => { this.data(); this.onstop?.(); }); }
  }
  const context = createContext({ Blob, navigator: { mediaDevices: missing ? undefined : { getUserMedia: async () => { requests++; return permission ? permission(stream) : stream; } } }, MediaRecorder: Capture,
    setTimeout: (fn, ms) => { const id = timers.size + 1; timers.set(id, { fn, ms }); return id; }, clearTimeout: id => timers.delete(id) });
  const source = await readFile(new URL('../src/recorder.ts', import.meta.url), 'utf8');
  const mod = new SourceTextModule(stripTypeScriptTypes(source), { context });
  await mod.link(() => { throw new Error('Unexpected dependency'); }); await mod.evaluate();
  const recorder = new mod.namespace.DreamRecorder({ onState: state => events.states.push(state), onError: error => events.errors.push(error), onAudio: blob => events.audio.push(blob) });
  return { recorder, track, captures, events, timers, stream, requests: () => requests, flush: () => { while (queued.length) queued.shift()(); } };
}

test('microphone is opt-in; finishing releases tracks and delivers a typed recording once', async () => {
  const h = await setup(); assert.equal(h.requests(), 0);
  await h.recorder.start(); await h.recorder.start(); assert.equal(h.requests(), 1);
  assert.equal(h.events.states.at(-1), 'recording'); assert.equal(h.track.stopped, false);
  h.recorder.finish(); h.recorder.finish(); h.flush();
  assert.equal(h.track.stopped, true); assert.equal(h.events.audio.length, 1);
  assert.equal(h.events.audio[0].type, 'audio/webm;codecs=opus'); assert.equal(h.timers.size, 0);
});
test('Safari uses MP4 when WebM is unsupported', async () => {
  const h = await setup({ supported: ['audio/mp4'] }); await h.recorder.start(); h.recorder.finish(); h.flush();
  assert.equal(h.events.audio[0].type, 'audio/mp4');
});
test('cancelling while the permission prompt is open stops a late stream and sends nothing', async () => {
  let resolve;
  const h = await setup({ permission: stream => new Promise(r => { resolve = () => r(stream); }) });
  const starting = h.recorder.start(); h.recorder.cancel(); resolve(); await starting;
  assert.equal(h.track.stopped, true); assert.equal(h.captures.length, 0); assert.equal(h.events.audio.length, 0);
});
test('repeated starts while permission is pending share one request', async () => {
  let resolve;
  const h = await setup({ permission: stream => new Promise(r => { resolve = () => r(stream); }) });
  const first = h.recorder.start(); await h.recorder.start(); assert.equal(h.requests(), 1);
  resolve(); await first; h.recorder.cancel();
});
test('leaving the screen cancels capture without transcription and clears the limit timer', async () => {
  const h = await setup(); await h.recorder.start(); h.captures[0].data(); h.recorder.cancel(); h.flush();
  assert.equal(h.track.stopped, true); assert.equal(h.events.audio.length, 0); assert.equal(h.timers.size, 0);
});
test('permission denial and unsupported recording are recoverable errors', async () => {
  const denied = await setup({ permission: async () => { throw new Error('denied'); } }); await denied.recorder.start();
  assert.deepEqual(denied.events.errors, ['permission']); assert.equal(denied.events.states.at(-1), 'idle');
  const unsupported = await setup({ missing: true }); await unsupported.recorder.start();
  assert.deepEqual(unsupported.events.errors, ['unsupported']); assert.equal(unsupported.requests(), 0);
});
test('recording has a two minute limit and stops before exceeding the upload allowance', async () => {
  const duration = await setup(); await duration.recorder.start();
  const timer = [...duration.timers.values()][0]; assert.equal(timer.ms, 120000); timer.fn(); duration.flush();
  assert.equal(duration.events.audio.length, 1); assert.equal(duration.track.stopped, true);
  const size = await setup(); await size.recorder.start(); size.captures[0].data(new Blob([new Uint8Array(7 * 1024 * 1024)])); size.flush();
  assert.equal(size.track.stopped, true); assert.equal(size.events.audio.length, 1);
});
test('device removal and recorder failure release the device and never send partial audio', async () => {
  const removed = await setup(); await removed.recorder.start(); removed.track.onended(); removed.flush();
  assert.equal(removed.track.stopped, true); assert.equal(removed.events.audio.length, 0); assert.deepEqual(removed.events.errors, ['permission']);
  const failed = await setup(); await failed.recorder.start(); failed.captures[0].onerror(); failed.flush();
  assert.equal(failed.events.audio.length, 0); assert.deepEqual(failed.events.errors, ['permission']);
});
