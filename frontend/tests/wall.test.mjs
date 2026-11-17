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

test('dreams spread over the brain ridges front to back, and a crowded brain still places every dream', async () => {
  const { pickRidges } = await load('brainShape.ts');
  const ridges = Array.from({ length: 40 }, (_, i) => [100 + (i % 10) * 50, 100 + Math.floor(i / 10) * 60]).flat();
  const few = pickRidges(ridges, 6);
  assert.equal(few.length, 6);
  assert.ok(Array.from(few).every((p, i) => i === 0 || p.x >= few[i - 1].x), 'front to back');
  let nearest = Infinity;
  for (let i = 0; i < few.length; i++) for (let j = i + 1; j < few.length; j++) nearest = Math.min(nearest, Math.hypot(few[i].x - few[j].x, few[i].y - few[j].y));
  assert.ok(nearest >= 100, `spread out, nearest ${nearest}`);
  const many = pickRidges(ridges, 55);
  assert.equal(many.length, 55);
  assert.equal(new Set(Array.from(many, p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)).size, 55);
  assert.deepEqual(Array.from(pickRidges(ridges, 6), p => ({ ...p })), Array.from(few, p => ({ ...p })));
  assert.equal(pickRidges([], 3).length, 0);
});
