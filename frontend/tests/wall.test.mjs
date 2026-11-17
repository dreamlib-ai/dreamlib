import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, createContext } from 'node:vm';

async function load(name) {
  const m = new SourceTextModule(stripTypeScriptTypes(await readFile(new URL(`../src/${name}`, import.meta.url), 'utf8')), { context: createContext({ Math, Uint8ClampedArray }) });
  await m.link(() => { throw new Error('unexpected dependency'); });
  await m.evaluate();
  return m.namespace;
}

test('the shelf case faces the reader in the middle and tips away further off, the same way on both sides', async () => {
  const { shelfPose, SHELF } = await load('shelf.ts');
  const middle = shelfPose(0, 400);
  assert.equal(Math.abs(middle.angle), 0);
  assert.equal(middle.front, true);
  const above = shelfPose(-300, 400), below = shelfPose(300, 400);
  assert.ok(above.angle > 0 && below.angle < 0);
  assert.equal(above.angle, -below.angle);
  assert.equal(shelfPose(-2000, 400).angle, SHELF.lean);
  assert.ok(shelfPose(-100, 400).angle < above.angle, 'closer cases lean less');
  assert.ok(middle.layer > above.layer && above.fade <= middle.fade);
  assert.equal(above.front, false);
});

test('BlurHash decodes to the colour it was made from and refuses broken hashes', async () => {
  const { decodeBlurhash } = await load('blurhash.ts');
  // backend/app/imagemeta.py encodes a flat (200, 100, 50) 64×48 picture to this hash
  // (the reference algorithm leaves small cosine terms even on a flat picture, so compare the mean colour)
  const flat = decodeBlurhash('L5M|T9}XfQ}X}XoKfQoKfQfQfQfQ', 64, 48);
  const mean = [0, 1, 2].map(c => flat.filter((_, i) => i % 4 === c).reduce((a, b) => a + b, 0) / (64 * 48));
  assert.ok(Math.abs(mean[0] - 200) <= 6 && Math.abs(mean[1] - 100) <= 6 && Math.abs(mean[2] - 50) <= 6, String(mean));
  const known = decodeBlurhash('LEHV6nWB2yk8pyo0adR*.7kCMdnj', 4, 3);
  assert.equal(known.length, 4 * 3 * 4);
  assert.ok([...known].every((v, i) => i % 4 !== 3 || v === 255));
  assert.equal(decodeBlurhash('', 4, 4), null);
  assert.equal(decodeBlurhash('LEHV6nWB2yk8', 4, 4), null);
  assert.equal(decodeBlurhash('LEHV6nWB2yk8pyo0adR*.7kCMdn"', 4, 4), null);
});

test('dreams spread evenly along the cortex line and skip the left-out cerebellum', async () => {
  const { spread, onCortex } = await load('brainShape.ts');
  const line = [...Array.from({ length: 11 }, (_, i) => ({ x: i * 10, y: 0 })), ...Array.from({ length: 11 }, (_, i) => ({ x: 300 + i * 10, y: 0 }))];
  const spots = spread(line, 4);
  assert.deepEqual(Array.from(spots, s => Math.round(s.x)), [25, 75, 325, 375]);
  assert.ok(spots.every(s => s.x <= 100 || s.x >= 300), 'no dream lands in the gap');
  assert.equal(spread(line, 0).length, 0);
  assert.equal(spread([], 3).length, 0);
  assert.equal(onCortex(60, 100), true);
  assert.equal(onCortex(300, 250), false);
  assert.equal(onCortex(230, 300), false);
});
