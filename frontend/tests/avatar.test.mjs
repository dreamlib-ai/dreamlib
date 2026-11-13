import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, createContext } from 'node:vm';
import { randomUUID } from 'node:crypto';

test('pending avatar references are owner-scoped, bounded and recoverable without signed URLs',async()=>{
  const rows=new Map();let now=Date.now();
  const context=createContext({localStorage:{getItem:k=>rows.get(k)??null,setItem:(k,v)=>rows.set(k,v),removeItem:k=>rows.delete(k)},Date:class extends Date{static now(){return now;}}});
  const mod=new SourceTextModule(stripTypeScriptTypes(await readFile(new URL('../src/avatar.ts',import.meta.url),'utf8')),{context});
  await mod.link(()=>{throw new Error('unexpected dependency');});await mod.evaluate();
  const api=mod.namespace;
  const pending={id:randomUUID(),spec:JSON.parse(JSON.stringify(api.defaultAvatar)),baseRevision:3};
  assert.ok(api.writeAvatarDraft('one',pending));assert.equal(api.readAvatarDraft('one').id,pending.id);
  assert.equal(api.readAvatarDraft('two'),null);
  assert.ok(![...rows.values()][0].includes('https://'));
  now+=86400001;assert.equal(api.readAvatarDraft('one'),null);assert.equal(rows.size,0);
  api.writeAvatarDraft('one',{...pending,spec:{...pending.spec,hair:'injected'}});
  assert.equal(api.readAvatarDraft('one'),null);
});
