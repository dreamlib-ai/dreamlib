import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, createContext } from 'node:vm';

test('effective features preserve provenance, respect empty corrections and fall back for legacy records', async () => {
  const m = new SourceTextModule(stripTypeScriptTypes(await readFile(new URL('../src/features.ts',import.meta.url),'utf8')), {context:createContext({})});
  await m.link(() => { throw new Error('unexpected runtime import'); }); await m.evaluate();
  const effective = m.namespace.effectiveFeatures;
  const model = {tags:['sea'],features:{version:1,genres:['fantasy'],perspective:'first-person',experiences:[{kind:'lucid',quote:'I knew I was dreaming.'}]}};
  const corrected = effective({...model,journal:{classification:{genres:[],experiences:[],tags:['family']}}});
  assert.equal(corrected.genres.length,0); assert.equal(corrected.experiences.length,0);
  assert.equal(corrected.tags[0],'family'); assert.equal(corrected.genreSource,'user');
  assert.equal(effective(model).genres[0],'fantasy');
  assert.equal(effective({...model,journal:{classification:null}}).experienceSource,'narrative');
  assert.equal(effective({tags:[]}).version,0); assert.equal(effective({tags:[]}).perspective,'unknown');
});
