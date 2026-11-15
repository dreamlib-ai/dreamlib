// The only place the web app talks to the API. Calls and wire types come from ./generated/api.ts, which
// scripts/gen_client.py writes from the backend's OpenAPI schema (S3); this file narrows the free-text
// fields the app knows more about and keeps the app's own call shapes.
import { getToken, publicAuthConfig } from './session';
import { tr } from './strings';
import type { ProductEvent } from './telemetry';
import type { AvatarSpec, PresetId } from './avatar';
import * as g from './generated/api';
import { ApiError } from './http';
import { WALL_PAGE } from './wall';

export { ApiError, type ErrorCode } from './http';
export type InterpretationType = 'universal' | 'cultural' | 'psychoanalytic';
export type ArtStyle = 'manga' | 'illustration' | 'collage' | 'photographic';
export type AvatarProfile = g.ProfileOut;
export const getSelfProfile = () => g.getProfile();
export const updateSelfProfile = (revision:number,changes:{displayName?:string;presetId?:PresetId;avatarJobId?:string;clearAvatar?:boolean}) => g.updateProfile({revision,...changes});
export const createAvatar = (requestId:string,spec:AvatarSpec,baseRevision:number) => g.createAvatar({requestId,spec,baseRevision});

export type DreamObject = g.DreamObjectOutput;
export type Emotion = g.EmotionOutput;
export type Features = g.FeaturesOutput;
export type Genre = Features['genres'][number];
export type Perspective = Features['perspective'];
export type Experience = Features['experiences'][number]['kind'];
export type ClassificationOverride = g.ClassificationOverrideInput;
export type Analysis = Omit<g.AnalysisOut, 'mood' | 'features' | 'analysisId'> & { mood?: string; features?: Features; analysisId?: string };

export type Panel = g.PanelOutput;
export type Job = g.JobOut;
export type DreamStatus = g.DreamStatus;

type Recall = '' | 'clear' | 'fragmentary' | 'faint';
export type Journal = Omit<g.Journal, 'classification' | 'recall'> & { classification?: ClassificationOverride | null; recall?: Recall };
export type Dream = Analysis & Omit<g.DreamOut, keyof g.AnalysisOut | 'type' | 'style' | 'visibility' | 'createdAt' | 'sleep' | 'revision' | 'journal'> & {
  type: InterpretationType;
  style: ArtStyle;
  visibility: 'private' | 'public';
  createdAt: string;
  sleep?: string;
  revision?: number;
  journal?: Journal;
};
/** The API sends these fields as free text; the app only ever stores its own values in them. */
const asDream = (d: g.DreamOut) => d as unknown as Dream;

export type JournalPatch = Omit<g.JournalPatch, 'revision' | 'classification' | 'recall'> & { classification?: ClassificationOverride | null; recall?: Recall };
export const editJournal = (dream: Dream, changes: JournalPatch) =>
  g.editJournal(dream.id, { revision: dream.revision ?? 0, ...changes }).then(asDream);

export const analyzeDream = (text: string, type: InterpretationType, context?: { mood?: string; sleep?: string; personal?: boolean; excludeId?: string }) =>
  g.analyze({ ...context, text, type });

export const cleanText = (text: string) => g.clean({ text });

export const startManga = (title: string, text: string, style: ArtStyle, panels: number, consistent = true, requestId?: string, signal?: AbortSignal, character?:{useAvatar:boolean;avatarRevision:number;perspective:Perspective}) =>
  g.startManga({ ...character, title, text, style, panels, consistent, requestId }, signal);

export const getJob = (id: string, signal?: AbortSignal) => g.getJob(id, signal);

export const getDream = (id: string, signal?: AbortSignal) => g.getDream(id, signal).then(asDream);

export const getDreamStatus = (id: string, signal?: AbortSignal) => g.dreamStatus(id, signal);

export const saveDream = (originalText: string, type: InterpretationType, analysis: Analysis, style: ArtStyle, panels: Panel[], jobId?: string, visibility: 'private' | 'public' = 'private', id?: string, existing = false) => {
  const body: g.DreamIn = { ...analysis, originalText, type, style, jobId, visibility, panels: panels.map(({ caption, path }) => ({ caption, path })) };
  return (id ? g.putDream(id, body, { existing }) : g.saveDream(body)).then(asDream);
};

export const redoJobPanel = (id: string, panel: number) => g.redoPanel(id, panel);

export const redoSavedPanel = (id: string, panel: number) => g.redoSavedPanel(id, panel);

export async function transcribeAudio(audio: Blob, language?: string, signal?: AbortSignal): Promise<string> {
  const token = await getToken();
  const headers: Record<string, string> = { 'Content-Type': audio.type || 'audio/webm' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const query = language ? `?lang=${encodeURIComponent(language)}` : '';
  const res = await fetch(`/api/v1/transcribe${query}`, { method: 'POST', headers, body: audio, signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data.error ?? tr.genericError, data.code ?? 'internal');
  return (data as { text: string }).text;  // raw audio upload: outside the generated client
}

export type Segment = g.Segment;
export type StreamSymbol = { id: string; text: string; glyph: string };
export type StreamProgress = { symbols: StreamSymbol[]; title: string; text: string };

/** G8: the interpretation written while the user waits (server-sent events, outside the generated client).
 * `onProgress` gets what has arrived so far; the promise ends with the whole answer, as `analyzeDream` gives it.
 * If the stream breaks after it started, the answer is asked for once more the plain way. */
export async function streamDream(text: string, type: InterpretationType, context: { mood?: string; sleep?: string; personal?: boolean; excludeId?: string },
  onProgress: (progress: StreamProgress) => void, signal?: AbortSignal): Promise<Analysis> {
  const token = await getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json', Accept: 'text/event-stream' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch('/api/v1/analyze/stream', { method: 'POST', headers, body: JSON.stringify({ ...context, text, type }), signal });
  if (!res.ok || !res.body) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, data.error ?? tr.genericError, data.code ?? 'internal');
  }
  const progress: StreamProgress = { symbols: [], title: '', text: '' };
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      let end: number;
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
        const kind = /^event: (.*)$/m.exec(block)?.[1];
        const data = JSON.parse(/^data: (.*)$/m.exec(block)?.[1] ?? '{}');
        if (kind === 'done') return data as Analysis;
        if (kind === 'error') throw new Error(data.message ?? tr.genericError);
        if (kind === 'entity') progress.symbols = [...progress.symbols, data as StreamSymbol];
        else if (kind === 'title') progress.title = data.text;
        else if (kind === 'text') progress.text += data.text;
        else continue;
        onProgress({ ...progress });
      }
    }
  } catch (cause) {
    if (signal?.aborted) throw cause;
  }
  return analyzeDream(text, type, context);  // the stream broke; its daily use is spent, this one is the retry
}

export const listDreams = () => g.listDreams().then((r) => r.dreams.map(asDream));

export type DreamPage = { dreams: Dream[]; next?: string };
/** G7: newest first, `limit` at a time; pass `next` back as the cursor until it is gone. */
export const listDreamPage = (cursor?: string, limit = WALL_PAGE, signal?: AbortSignal): Promise<DreamPage> =>
  g.listDreams({ limit, cursor }, signal).then((r) => ({ dreams: r.dreams.map(asDream), next: r.next }));

export const deleteDream = (id: string) => g.deleteDream(id);

/** R2: every dream, journal, consent, magazine and reading as one JSON file. */
export async function exportAccount(): Promise<Blob> {
  const data = await g.exportAccount();
  return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
}
/** R2: deletes the account and everything in it; cannot be undone. */
export const deleteAccount = () => g.deleteAccount({ confirm: 'delete' });

export type Magazine = g.MagazineOut;
export type MagazinePage = g.MagazinePage;
/** G4: the dream's laid-out magazine; 404 (ApiError) until the job has made it or when there is no booklet. */
export const getMagazine = (dreamId: string, signal?: AbortSignal) => g.magazine(dreamId, signal);
/** G6: open the magazine to anyone with the link, or close it again; the link stays the same. */
export const shareMagazine = (dreamId: string, visibility: 'private' | 'link') => g.shareMagazine(dreamId, { visibility });
export type SharedMagazine = g.SharedMagazineOut;
/** G6: a shared magazine, read without signing in. */
export const getSharedMagazine = (slug: string, signal?: AbortSignal) => g.sharedMagazine(slug, signal);
export const sharedPath = (slug: string) => `/m/${slug}`;
/** F2: the magazine of a dream from this night a year ago, by the dreamer's own date and time zone. */
export function getAnniversary(signal?: AbortSignal) {
  const now = new Date();
  const on = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  return g.anniversary({ on, tz: -now.getTimezoneOffset() }, signal);
}

export type Brain = g.BrainOut;
export type BrainDream = g.BrainDream;
export type BrainLink = g.BrainLink;
export type Relation = g.BrainLink['relation'];
export const getBrain = (signal?: AbortSignal) => g.brain(signal);
/** BG4: link two dreams by hand, or hide a scored link between them; answers the new graph. */
export const editBrain = (a: string, b: string, action: 'link' | 'hide', on = true) => g.editBrain({ a, b, action, on });

export const trackEvent = (name: ProductEvent, eventId: string, platform: g.EventIn['platform']) =>
  g.event({ name, eventId, platform });

export async function checkGoogleProvider(): Promise<void> {
  const { url, key } = publicAuthConfig();
  const response = await fetch(`${url}/auth/v1/settings`, { headers: { apikey: key } });
  if (!response.ok) throw new Error(tr.auth.failed);
  const settings = await response.json();
  if (settings.external?.google !== true) throw new Error(tr.auth.googleDisabled);
}
