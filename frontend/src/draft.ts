import type { Analysis, ArtStyle, Panel, Perspective } from './api';

export type Draft = {
  id: string; text: string; mode: 'voice' | 'text'; analysis: Analysis | null;
  style: ArtStyle; count: number; panels: Panel[]; jobId?: string;
  jobStatus: 'none' | 'pending' | 'done' | 'failed'; recorded: boolean; saved: boolean;
  personal: boolean;
  useAvatar:boolean; perspective:Perspective; jobUseAvatar:boolean; jobAvatarRevision:number; jobPerspective:Perspective;
};
const prefix = 'dreamlib:draft:v1:';
const maxAge = 24 * 60 * 60 * 1000;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const string = (v: unknown): v is string => typeof v === 'string';

export function newDraft(): Draft {
  return { id: crypto.randomUUID(), text: '', mode: 'voice', analysis: null, style: 'manga', count: 4,
    panels: [], jobStatus: 'none', recorded: false, saved: false, personal: false,
    useAvatar:true,perspective:'unknown',jobUseAvatar:false,jobAvatarRevision:0,jobPerspective:'unknown' };
}

export function readDraft(owner: string): Draft | null {
  try {
    const raw = localStorage.getItem(prefix + owner);
    if (!raw) return null;
    if (raw.length > 80_000) throw new Error('oversize');
    const { updatedAt, value: d } = JSON.parse(raw);
    if (!Number.isFinite(updatedAt) || Date.now() - updatedAt > maxAge || updatedAt > Date.now() + 60_000) throw new Error('expired');
    if (!d || !uuid.test(d.id) || !string(d.text) || d.text.length > 16_000 || !['voice', 'text'].includes(d.mode)
      || !['manga', 'illustration', 'collage', 'photographic'].includes(d.style) || ![4, 6, 9].includes(d.count)
      || !['none', 'pending', 'done', 'failed'].includes(d.jobStatus) || (d.jobId && !uuid.test(d.jobId))
      || !Array.isArray(d.panels) || d.panels.length > 9 || !d.panels.every((p: Panel) => string(p.path) && string(p.caption))
      || typeof d.recorded !== 'boolean' || typeof d.saved !== 'boolean') throw new Error('invalid');
    const a = d.analysis;
    if (a !== null && (!a || !string(a.title) || !string(a.cleanText) || !string(a.interpretation)
      || !Array.isArray(a.tags) || !a.tags.every(string) || !Array.isArray(a.objects)
      || !a.objects.every((o: {label: unknown; meaning: unknown}) => o && string(o.label) && string(o.meaning))
      || !Array.isArray(a.emotions) || !a.emotions.every((e: {label: unknown; pct: number}) => e && string(e.label) && Number.isFinite(e.pct)))) throw new Error('invalid');
    if (d.jobStatus !== 'none' && (!d.jobId || !a)) throw new Error('invalid job');
    if (d.personal !== undefined && typeof d.personal !== 'boolean') throw new Error('invalid preference');
    // A malformed new field must not destroy an otherwise recoverable older draft.
    if (a?.features && (!Array.isArray(a.features.genres) || !Array.isArray(a.features.experiences)
      || !Array.isArray(a.features.people) || !Array.isArray(a.features.places) || !Array.isArray(a.features.events)
      || !a.features.experiences.every((e: {kind?: unknown; quote?: unknown}) => e && string(e.kind) && string(e.quote)))) delete a.features;
    d.personal = d.personal === true; // migrate existing v1 drafts without erasing their text
    const cameras=['unknown','first-person','observer','mixed'];
    d.useAvatar=typeof d.useAvatar==='boolean'?d.useAvatar:true;
    d.perspective=cameras.includes(d.perspective)?d.perspective:'unknown';
    d.jobUseAvatar=d.jobUseAvatar===true;
    d.jobAvatarRevision=Number.isInteger(d.jobAvatarRevision)&&d.jobAvatarRevision>=0?d.jobAvatarRevision:0;
    d.jobPerspective=cameras.includes(d.jobPerspective)?d.jobPerspective:'unknown';
    return d as Draft;
  } catch { clearDraft(owner); return null; }
}

export function writeDraft(owner: string, value: Draft): boolean {
  try {
    // Signed URLs expire; restore them from the authenticated job endpoint instead.
    const panels = value.panels.map(({ path, caption }) => ({ path, caption }));
    localStorage.setItem(prefix + owner, JSON.stringify({ updatedAt: Date.now(), value: { ...value, panels } }));
    return true;
  } catch { return false; }
}

export function clearDraft(owner: string) {
  try { localStorage.removeItem(prefix + owner); } catch { /* Private browsing may deny storage. */ }
}
