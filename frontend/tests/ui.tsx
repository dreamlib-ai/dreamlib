/** Dev-only UI harness. Synthetic audio + local responses; no device permission or paid API. */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../src/fonts.css';
import '../src/theme.css';
import '../src/app.css';
import '../src/workspace.css';
import '../src/atmosphere.css';
import '../src/editorial.css';
import '../src/magazine.css';
import { Workspace } from '../src/App';
import { SharedMagazinePage } from '../src/Magazine';
import Onboarding from '../src/Onboarding';
import type { Dream } from '../src/api';
import { defaultAvatar } from '../src/avatar';

const params = new URLSearchParams(location.search);
const dream: Dream = { id: 'test-dream', title: 'Denizin üstünde', originalText: 'Gece denizin üstünde uçuyordum. Aşağıda ışıkları yanan bir şehir vardı.', cleanText: 'Denizin üstünde uçuyordum.', interpretation: 'Denizin üstünde uçmak, özgürlük isteğini ve bilinmeyene duyulan merakı çağrıştırabilir. Rüyandaki huzur, bu değişime açık olduğunu düşündürüyor. Bu sahnenin senin için anlamını kendi hislerinle birlikte değerlendirebilirsin.', tags: ['Deniz', 'Uçmak'], objects: [{ label: 'Deniz', meaning: 'Keşfetmek istediğin duyguları hatırlatabilir.' }], emotions: [{ label: 'Huzur', pct: 70, note: '' }, { label: 'Merak', pct: 30, note: '' }], type: 'universal', style: 'manga', panels: [], visibility: 'private', createdAt: '2026-11-01T06:00:00Z' };
const testKey = 'dreamlib:ui-recovery';
dream.features = {version:1, genres:['fantasy','adventure'], perspective:'first-person', people:[], places:['deniz'], events:['uçmak'], experiences:[]};
if (params.has('reset')) { localStorage.removeItem(testKey); localStorage.removeItem('dreamlib:draft:v1:test'); localStorage.removeItem('dreamlib:avatar-draft:v1:test'); }
const fake = JSON.parse(localStorage.getItem(testKey) ?? '{"rows":[],"jobs":{}}');
fake.profile ??= {id:'test',displayName:'',avatar:null,avatarUrl:'',presetId:null,revision:0};
// ?wall: 60 dreams with pictures of many shapes (G3 sizes, colour, BlurHash) and some text-only ones (G7).
const shapes = [[1024,1024],[832,1216],[1216,832],[768,1344],[1024,1536]];
const pictures = ['/avatar-512.png','/avatars/ink.webp','/favicon.png'];
const wallRows = (): Dream[] => Array.from({length:60}, (_, i) => ({ ...dream, id:`wall-${i}`, title: i % 7 === 3 ? 'Uzun bir koridorun sonunda, hiç görmediğim bir kapının önünde bekliyordum' : `Rüya ${60 - i}`,
  createdAt: new Date(Date.UTC(2026, 10, 14) - i * 86400000).toISOString(),
  panels: i % 5 === 2 ? [] : [{ path:`wall/${i}`, caption:'', url: pictures[i % 3], thumb: pictures[i % 3], width: shapes[i % 5][0], height: shapes[i % 5][1], color: ['#203252','#5a3b6e','#2e5a4f'][i % 3], blurhash: i % 2 ? 'LEHV6nWB2yk8pyo0adR*.7kCMdnj' : '' }] }));
// ?magazine: one dream with a five-picture booklet and its laid-out magazine (G5).
const bookletRow = (): Dream => ({ ...dream, id:'booklet', title:'Denizin üstündeki şehir', panels: [0,1,2,3,4].map(i => ({ path:`book/${i}`, caption:`Sahne ${i + 1}: ışıkları yanan şehrin üstünden geçiyorum`, url: pictures[i % 3], width: [832,1216,1216,1024,832][i], height: [1216,832,832,1024,1216][i], color: ['#203252','#5a3b6e','#2e5a4f'][i % 3], blurhash:'LEHV6nWB2yk8pyo0adR*.7kCMdnj' })) });
const fakeMagazine = (row: Dream) => ({ id:'mag-1', dreamId:row.id, status:'ready', visibility:'private', updatedAt:'2026-11-14T07:00:00Z', panels: row.panels,
  spec: { version:1, cover:{ title:row.title, panel:0, color:'#203252' }, colophon:{ dated:'2026-11-13', style:'manga', tags:row.tags, emotions:['Huzur','Merak'] },
    pages:[{layout:'full',panels:[0],text:''},{layout:'pair',panels:[1,2],text:''},{layout:'quote',panels:[],text:'Denizin üstünde uçmak, özgürlük isteğini ve bilinmeyene duyulan merakı çağrıştırabilir.'},{layout:'full',panels:[3],text:''},{layout:'full',panels:[4],text:''}] } });
const shareState = { visibility: 'private' };
const rows: Dream[] = params.has('magazine') ? [bookletRow()] : params.has('themes') ? [dream, { ...dream, id:'second-dream', title:'Ormandaki ışık', tags:['DENİZ','orman'], features:{...dream.features,genres:['scifi']} }, { ...dream, id:'third-dream', title:'Eski ev', tags:['ev'], features:{...dream.features,genres:['daily']}, emotions:[{label:'Korku',pct:100,note:''}] }] : params.has('populated') ? [dream] : params.has('wall') ? wallRows() : fake.rows;
const persist = () => { localStorage.setItem(testKey, JSON.stringify({ ...fake, rows })); trace(); };
const calls: { path: string; method: string; bytes?: number; text?: string }[] = [];
// A visible, read-only test trace in the DOM lets browser checks inspect requests.
function trace() {
  const element = document.querySelector('#test-trace') ?? document.body.appendChild(Object.assign(document.createElement('script'), { id: 'test-trace', type: 'application/json' }));
  element.textContent = JSON.stringify({ calls, records: rows.length, jobs: Object.keys(fake.jobs).length });
}
let transcripts = 0;
globalThis.fetch = async (input, init) => {
  const path = new URL(String(input), location.origin).pathname;
  const payload = typeof init?.body === 'string' ? JSON.parse(init.body) : {};
  calls.push({ path, method: init?.method ?? 'GET', text: payload.text ?? payload.originalText, personal: payload.personal, excludeId: payload.excludeId, useAvatar:payload.useAvatar,avatarRevision:payload.avatarRevision,perspective:payload.perspective, bytes: init?.body instanceof Blob ? init.body.size : undefined }); trace();
  const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
  if (path === '/api/v1/events') return new Response(null, { status: 204 });
  if(path==='/api/v1/profile') {
    if(init?.method==='PATCH') {
      if(payload.revision!==fake.profile.revision)return json({error:'Profile changed'},409);
      if(payload.displayName!==undefined)fake.profile.displayName=payload.displayName;
      if(payload.presetId)Object.assign(fake.profile,{presetId:payload.presetId,avatar:{...defaultAvatar,...(payload.presetId==='ink'?{hair:'bun',hairColor:'black',accessory:'glasses'}:{})},avatarUrl:`/avatars/${payload.presetId}.webp`});
      if(payload.avatarJobId)Object.assign(fake.profile,{presetId:null,avatar:fake.jobs[payload.avatarJobId].spec,avatarUrl:'/avatars/ink.webp'});
      if(payload.clearAvatar)Object.assign(fake.profile,{presetId:null,avatar:null,avatarUrl:''});
      fake.profile.revision++;persist();
    }
    return json(fake.profile);
  }
  if(path==='/api/v1/avatar') {
    if(!fake.jobs[payload.requestId]) {
      fake.jobs[payload.requestId]={kind:'avatar',spec:payload.spec,ready:Date.now()+(params.has('delayAvatar')?8000:0)};persist();
      if(params.has('lostAvatar'))throw new TypeError('Lost avatar response');
    }
    return json({id:payload.requestId});
  }
  if (path === '/api/v1/transcribe') {
    if (params.has('slow')) return new Promise<Response>((_resolve, reject) => init?.signal?.addEventListener('abort', () => reject(new DOMException('Test abort', 'AbortError'))));
    if (params.has('retry') && ++transcripts === 1) return json({ error: 'test retry' }, 502);
    return json({ text: dream.originalText });
  }
  if (path === '/api/v1/analyze') return json(dream);
  if (path === '/api/v1/dreams' && init?.method === 'POST') { const saved = { ...dream, ...payload }; rows.push(saved); return json(saved); }
  if (path.endsWith('/magazine/visibility') && init?.method === 'PUT') {
    const row = rows.find(d => d.id === path.split('/')[4]);
    if (!row) return json({ error:'bu rüyanın dergisi yok', code:'not_found' }, 404);
    shareState.visibility = payload.visibility;
    return json({ ...fakeMagazine(row), visibility: shareState.visibility, ...(shareState.visibility === 'link' ? { shareSlug: 'abcDEF123_-x' } : {}) });
  }
  if (path.startsWith('/api/v1/dreams/') && init?.method === 'PUT') {
    const saved = { ...dream, ...payload, id: path.split('/').pop(), panels: (payload.panels ?? []).map((p: object) => ({ ...p, url:'/favicon.png' })) };
    const index = rows.findIndex(row => row.id === saved.id);
    if (index < 0) rows.push(saved); else rows[index] = saved;
    persist(); return json(saved);
  }
  if (path.startsWith('/api/v1/m/')) {
    return params.has('gone') ? json({ error:'bu dergi paylaşılmıyor', code:'not_found' }, 404) : json({ spec: fakeMagazine(bookletRow()).spec, panels: bookletRow().panels });
  }
  if (path.startsWith('/api/v1/dreams/') && path.endsWith('/magazine')) {
    const row = rows.find(d => d.id === path.split('/')[4]);
    return row?.panels.length ? json(fakeMagazine(row)) : json({ error:'bu rüyanın dergisi yok', code:'not_found' }, 404);
  }
  if (path === '/api/v1/dreams') {
    const query = new URL(String(input), location.origin).searchParams;
    const start = Number(query.get('cursor') ?? 0), limit = Number(query.get('limit') ?? 200);
    const page = rows.slice(start, start + limit);
    if (params.has('slowPages') && start) await new Promise(done => setTimeout(done, 700));
    return json(start + limit < rows.length ? { dreams: page, next: String(start + limit) } : { dreams: page });
  }
  if (path.endsWith('/journal') && init?.method === 'PATCH') {
    const row = rows.find(d => d.id === path.split('/')[3]);
    if (!row) return json({error:'not found'},404);
    if ((row.revision ?? 0) !== payload.revision) return json({error:'revision conflict'},409);
    row.journal ??= { dreamedOn:null, favorite:false, reflection:'', firstText:'', entries:[], analysisStale:false, artStale:false };
    if (payload.title !== undefined) row.title = payload.title;
    if (payload.originalText !== undefined && payload.originalText !== row.originalText) {
      row.journal.firstText ||= row.originalText;
      row.originalText = payload.originalText; row.journal.analysisStale = true;
    }
    for (const key of ['dreamedOn','favorite','reflection','classification','recall'] as const) if (payload[key] !== undefined) Object.assign(row.journal, {[key]:payload[key]});
    if (payload.addition) { row.journal.entries.push({...payload.addition,createdAt:new Date().toISOString()}); row.journal.analysisStale=true; }
    if (payload.refresh) row.journal.analysisStale=false;
    row.revision = (row.revision ?? 0) + 1; persist(); return json(row);
  }
  if (path === '/api/v1/manga') {
    const id = payload.requestId;
    if (!fake.jobs[id]) {
      fake.jobs[id] = { ready: Date.now() + (params.has('recovery') ? 12000 : 0) }; persist();
      if (params.has('lost')) throw new TypeError('Simulated lost response after queue commit');
    }
    return json({ id });
  }
  if (path.startsWith('/api/v1/jobs/')) {
    const id = path.split('/').pop();
    const pending = Date.now() < (fake.jobs[id]?.ready ?? 0);
    if(fake.jobs[id]?.kind==='avatar')return json({id,status:pending?'running':'done',total:1,done:pending?0:1,panels:pending?[]:[{path:'test/avatar',url:'/avatars/ink.webp',caption:''}],error:''});
    return json({ id, status: pending ? 'running' : 'done', total:4, done:pending ? 1 : 4,
      panels: pending ? [] : [0,1,2,3].map(n => ({ path:`test/panel-${n}`, caption:`Sahne ${n}`, url:'/favicon.png' })), error:'' });
  }
  if (path === '/api/v1/jobs/test-booklet') return json({ id: 'test-booklet', status: 'done', total: 4, done: 4, panels: [], error: '' });
  throw new Error(`Network request blocked in test harness: ${path}`);
};
// Oscillator feeds a MediaStream destination only; nothing is played through speakers.
Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => {
  if (params.has('denied')) throw new DOMException('Test denial', 'NotAllowedError');
  const context = new AudioContext();
  const oscillator = context.createOscillator();
  const destination = context.createMediaStreamDestination();
  oscillator.connect(destination); oscillator.start();
  destination.stream.getTracks().forEach(track => {
    const stop = track.stop.bind(track);
    track.stop = () => { stop(); oscillator.stop(); void context.close(); };
  });
  return destination.stream;
} } });
const account = { id: 'test', email: '', provider: '', profile: { onboarded: true, visibility: 'private' as const } };
createRoot(document.getElementById('root')!).render(<StrictMode>{params.has('shared') ? <SharedMagazinePage slug="abcDEF123_-x" /> : params.has('onboarding') || params.has('privacy')
  ? <Onboarding account={params.has('privacy') ? account : null} replay={false} initialError="" onDone={async () => {}} />
  : <Workspace account={account} onSignOut={() => {}} />}</StrictMode>);
