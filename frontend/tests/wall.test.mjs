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

test('the wall puts each card under the shortest column and never moves earlier cards', async () => {
  const { placeCards, wallColumns } = await load('wall.ts');
  assert.deepEqual({ ...wallColumns(375) }, { count: 2, gap: 12 });
  assert.equal(wallColumns(700).count, 3);
  assert.equal(wallColumns(1050).count, 4);
  const first = placeCards([300, 100, 100, 50], 2, 100, 10);
  assert.deepEqual(first.spots.map(s => ({ ...s })), [{ x: 0, y: 0 }, { x: 110, y: 0 }, { x: 110, y: 110 }, { x: 110, y: 220 }]);
  assert.equal(first.height, 300);
  const longer = placeCards([300, 100, 100, 50, 80], 2, 100, 10);
  assert.deepEqual(longer.spots.slice(0, 4).map(s => ({ ...s })), first.spots.map(s => ({ ...s })));
  assert.equal(placeCards([], 3, 100, 10).height, 0);
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

test('the island gives each feeling a slice, keeps cards apart and puts the newest dreams nearest the centre', async () => {
  const { islandLayout, CARD } = await load('island.ts');
  const feelings = ['huzur', 'huzur', 'huzur', 'korku', 'merak', '', 'öfke', 'sevinç', 'özlem', 'şaşkınlık'];
  const dreams = Array.from({ length: 120 }, (_, i) => ({ id: `d${i}`, day: `2026-${String(1 + (i % 12)).padStart(2, '0')}-${String(1 + (i % 28)).padStart(2, '0')}`, feeling: feelings[i % feelings.length] }));
  const { spots, districts, radius } = islandLayout(dreams);
  assert.equal(spots.length, 120);
  assert.equal(new Set(spots.map(s => s.id)).size, 120);
  assert.ok(districts.length <= 6);
  assert.ok(Math.abs(districts.at(-1).to - districts[0].from - Math.PI * 2) < 1e-9);
  for (let i = 0; i < spots.length; i++) for (let j = i + 1; j < spots.length; j++)
    assert.ok(Math.hypot(spots[i].x - spots[j].x, spots[i].z - spots[j].z) >= CARD.width, `${spots[i].id} and ${spots[j].id} overlap`);
  assert.ok(spots.every(s => Math.hypot(s.x, s.z) < radius));
  const calm = spots.filter(s => s.district === 0).map(s => ({ r: Math.hypot(s.x, s.z), day: dreams.find(d => d.id === s.id).day }));
  for (let i = 1; i < calm.length; i++) assert.ok(calm[i].r >= calm[i - 1].r - 1e-9 && calm[i].day <= calm[i - 1].day);
  assert.deepEqual(islandLayout(dreams).spots.map(s => ({ ...s })), spots.map(s => ({ ...s })));
  const one = islandLayout([{ id: 'a', day: '2026-01-01', feeling: '' }]);
  assert.equal(one.spots.length, 1);
  assert.equal(islandLayout([]).spots.length, 0);
});
