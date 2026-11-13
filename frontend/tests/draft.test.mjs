import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, createContext } from 'node:vm';
import { randomUUID } from 'node:crypto';

async function harness() {
  const rows = new Map(); let now = Date.now();
  const storage = { getItem: k => rows.get(k) ?? null, setItem: (k,v) => rows.set(k,v), removeItem: k => rows.delete(k) };
  const context = createContext({ localStorage: storage, crypto: { randomUUID }, Date: class extends Date { static now() { return now; } } });
  const m = new SourceTextModule(stripTypeScriptTypes(await readFile(new URL('../src/draft.ts', import.meta.url),'utf8')), { context });
  await m.link(() => { throw new Error('unexpected runtime dependency'); }); await m.evaluate();
  return { api: m.namespace, rows, storage, expire: () => { now += 25 * 60 * 60 * 1000; } };
}

test('reload preserves owner-scoped identity, text and queued request without storing signed URLs or audio', async () => {
  const { api, rows } = await harness(); const d = api.newDraft();
  d.text = 'A private dream'; d.mode = 'text'; d.panels = [{path:'owner/panel',caption:'scene',url:'https://signed.example/secret'}];
  assert.equal(api.writeDraft('a',d),true);
  assert.equal(api.readDraft('a').id,d.id); assert.equal(api.readDraft('a').text,d.text);
  assert.equal(api.readDraft('b'),null); assert.equal([...rows.values()][0].includes('signed.example'),false);
  api.clearDraft('b'); assert.ok(api.readDraft('a')); api.clearDraft('a'); assert.equal(api.readDraft('a'),null);
});

test('expired and malformed drafts are removed, unavailable storage is recoverable', async () => {
  const { api, rows, storage, expire } = await harness();
  api.writeDraft('a',api.newDraft()); expire(); assert.equal(api.readDraft('a'),null); assert.equal(rows.size,0);
  rows.set('dreamlib:draft:v1:a','{"value":{"id":"broken"}}'); assert.equal(api.readDraft('a'),null); assert.equal(rows.size,0);
  storage.setItem = () => { throw new Error('denied'); }; assert.equal(api.writeDraft('a',api.newDraft()),false);
});


test('personal history choice is opt-in and migrates old drafts without losing text', async () => {
  const { api } = await harness(); const d = api.newDraft();
  assert.equal(d.personal,false); d.personal=true; api.writeDraft('a',d); assert.equal(api.readDraft('a').personal,true);
  delete d.personal; d.text='old draft'; api.writeDraft('a',d);
  assert.equal(api.readDraft('a').personal,false); assert.equal(api.readDraft('a').text,'old draft');
});

test('malformed classification metadata does not erase an otherwise valid dream draft', async () => {
  const { api } = await harness(); const d=api.newDraft();
  d.text='remembered text';
  d.analysis={title:'T',cleanText:'C',interpretation:'I',tags:[],objects:[],emotions:[],features:{genres:'invalid'}};
  api.writeDraft('a',d);
  const restored=api.readDraft('a');
  assert.equal(restored.text,'remembered text'); assert.equal(restored.analysis.title,'T');
  assert.equal(restored.analysis.features,undefined);
});

test('legacy queued booklets retain the original no-avatar request snapshot', async()=>{
  const {api}=await harness();const d=api.newDraft();
  d.analysis={title:'T',cleanText:'C',interpretation:'I',tags:[],objects:[],emotions:[]};
  d.jobId=randomUUID();d.jobStatus='pending';
  delete d.jobUseAvatar;delete d.jobAvatarRevision;delete d.jobPerspective;delete d.useAvatar;
  api.writeDraft('a',d);const restored=api.readDraft('a');
  assert.equal(restored.useAvatar,true);assert.equal(restored.jobUseAvatar,false);
  assert.equal(restored.jobAvatarRevision,0);assert.equal(restored.jobPerspective,'unknown');
});
