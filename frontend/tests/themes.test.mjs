import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, createContext } from 'node:vm';

test('themes count distinct dreams, normalize Turkish tags and ignore single occurrences', async () => {
  const m = new SourceTextModule(stripTypeScriptTypes(await readFile(new URL('../src/themes.ts',import.meta.url),'utf8')), {context:createContext({})});
  await m.link(() => {throw new Error('unexpected dependency');}); await m.evaluate();
  const count=m.namespace.recurringThemes;
  assert.deepEqual(JSON.parse(JSON.stringify(count([{id:'a',tags:['DENİZ','deniz','']},{id:'a',tags:['deniz']},{id:'b',tags:['  deniz ','ev']}]))),[{label:'deniz',count:2}]);
  assert.equal(count([{id:'one',tags:['same','same']}]).length,0);
  assert.equal(count(Array.from({length:16},(_,i)=>({id:String(i),tags:[i===15?'outside':'inside']})))[0].count,15);
});
