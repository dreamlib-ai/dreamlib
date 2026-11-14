// The only place the web app talks to the API.
import { getToken, publicAuthConfig } from './session';
import { tr } from './strings';
import type { ProductEvent } from './telemetry';
import type { AvatarSpec, PresetId } from './avatar';

export type InterpretationType = 'universal' | 'cultural' | 'psychoanalytic';
/** Machine codes from docs/api.md (S2); the message is for people and may change. */
export type ErrorCode = 'invalid_request' | 'auth_required' | 'auth_invalid' | 'not_found' | 'conflict' | 'revision_conflict'
  | 'job_busy' | 'too_large' | 'unsupported_media' | 'unreadable' | 'daily_limit' | 'rate_limited' | 'upstream_failed'
  | 'service_off' | 'internal';
export class ApiError extends Error {
  status: number;
  code: ErrorCode;
  constructor(status:number,message:string,code:ErrorCode='internal') { super(message); this.status=status; this.code=code; }
}
export type AvatarProfile = { id:string; displayName:string; avatar:AvatarSpec|null; presetId:PresetId|null; avatarUrl:string; revision:number };
export const getSelfProfile = () => request<AvatarProfile>('GET','/api/v1/profile');
export const updateSelfProfile = (revision:number,changes:{displayName?:string;presetId?:PresetId;avatarJobId?:string;clearAvatar?:boolean}) => request<AvatarProfile>('PATCH','/api/v1/profile',{revision,...changes});
export const createAvatar = (requestId:string,spec:AvatarSpec,baseRevision:number) => request<{id:string}>('POST','/api/v1/avatar',{requestId,spec,baseRevision});
export type ArtStyle = 'manga' | 'illustration' | 'collage' | 'photographic';

export type DreamObject = { label: string; meaning: string };
export type Emotion = { label: string; pct: number; note: string };
export type Genre = 'daily' | 'fantasy' | 'scifi' | 'romance' | 'adventure' | 'suspense';
export type Perspective = 'first-person' | 'observer' | 'mixed' | 'unknown';
export type Experience = 'lucid' | 'recurring' | 'nightmare';
export type Features = { version: number; genres: Genre[]; perspective: Perspective; people: string[]; places: string[]; events: string[]; experiences: { kind: Experience; quote: string }[] };
export type ClassificationOverride = { genres?: Genre[] | null; perspective?: Perspective | null; experiences?: Experience[] | null; tags?: string[] | null };
export type Analysis = {
  title: string;
  cleanText: string;
  tags: string[];
  interpretation: string;
  objects: DreamObject[];
  emotions: Emotion[];
  mood?: string;
  features?: Features;
};

export type Panel = { caption: string; path: string; url?: string };
export type Job = { id: string; status: 'running' | 'done' | 'failed'; done: number; total: number; panels: Panel[]; error: string; etaSeconds?: number };

export type Dream = Analysis & {
  id: string;
  originalText: string;
  type: InterpretationType;
  style: ArtStyle;
  panels: Panel[];
  visibility: 'private' | 'public';
  createdAt: string;
  sleep?: string;
  revision?: number;
  journal?: Journal;
};

export type Journal = { dreamedOn: string | null; favorite: boolean; reflection: string; firstText: string; classification?: ClassificationOverride | null; recall?: '' | 'clear' | 'fragmentary' | 'faint';
  entries: { id: string; text: string; createdAt: string }[]; analysisStale: boolean; artStale: boolean };
export type JournalPatch = { title?: string; originalText?: string; dreamedOn?: string | null; favorite?: boolean;
  reflection?: string; addition?: { id: string; text: string }; refresh?: boolean; personal?: boolean;
  classification?: ClassificationOverride | null; recall?: '' | 'clear' | 'fragmentary' | 'faint' };
export const editJournal = (dream: Dream, changes: JournalPatch) =>
  request<Dream>('PATCH', `/api/v1/dreams/${dream.id}/journal`, { revision: dream.revision ?? 0, ...changes });

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = await getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal?.aborted) cancel();
  signal?.addEventListener('abort', cancel, { once: true });
  const timeout = window.setTimeout(cancel, 60_000);
  try {
    const res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal });
    if (res.status === 204) return undefined as T;
    const data = await res.json().catch((cause) => {
      if (controller.signal.aborted) throw cause;
      if (res.ok) throw new Error(tr.genericError);
      return {};
    });
    if (!res.ok) throw new ApiError(res.status,data.error ?? tr.genericError,data.code ?? 'internal');
    return data as T;
  } catch (cause) {
    if (controller.signal.aborted && !signal?.aborted) throw new Error(tr.recovery.timeout);
    throw cause;
  } finally { window.clearTimeout(timeout); signal?.removeEventListener('abort', cancel); }
}

export const analyzeDream = (text: string, type: InterpretationType, context?: { mood?: string; sleep?: string; personal?: boolean; excludeId?: string }) =>
  request<Analysis>('POST', '/api/v1/analyze', { ...context, text, type });

export const cleanText = (text: string) =>
  request<{ cleanText: string; language: string }>('POST', '/api/v1/clean', { text });

export const startManga = (title: string, text: string, style: ArtStyle, panels: number, consistent = true, requestId?: string, signal?: AbortSignal, character?:{useAvatar:boolean;avatarRevision:number;perspective:Perspective}) =>
  request<{ id: string }>('POST', '/api/v1/manga', { ...character, title, text, style, panels, consistent, requestId }, signal);

export const getJob = (id: string, signal?: AbortSignal) => request<Job>('GET', `/api/v1/jobs/${id}`, undefined, signal);

export const getDream = (id: string, signal?: AbortSignal) => request<Dream>('GET', `/api/v1/dreams/${id}`, undefined, signal);

export const saveDream = (originalText: string, type: InterpretationType, analysis: Analysis, style: ArtStyle, panels: Panel[], jobId?: string, visibility: 'private' | 'public' = 'private', id?: string, existing = false) =>
  request<Dream>(id ? 'PUT' : 'POST', id ? `/api/v1/dreams/${id}?existing=${existing}` : '/api/v1/dreams', { ...analysis, originalText, type, style, jobId, visibility, panels: panels.map(({ caption, path }) => ({ caption, path })) });

export const redoJobPanel = (id: string, panel: number) =>
  request<Panel>('POST', `/api/v1/jobs/${id}/panels/${panel}/redo`);

export const redoSavedPanel = (id: string, panel: number) =>
  request<Panel>('POST', `/api/v1/dreams/${id}/panels/${panel}/redo`);

export async function transcribeAudio(audio: Blob, language?: string, signal?: AbortSignal): Promise<string> {
  const token = await getToken();
  const headers: Record<string, string> = { 'Content-Type': audio.type || 'audio/webm' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const query = language ? `?lang=${encodeURIComponent(language)}` : '';
  const res = await fetch(`/api/v1/transcribe${query}`, { method: 'POST', headers, body: audio, signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data.error ?? tr.genericError, data.code ?? 'internal');
  return data.text;
}

export const listDreams = () => request<{ dreams: Dream[] }>('GET', '/api/v1/dreams').then((r) => r.dreams);

export const deleteDream = (id: string) => request<void>('DELETE', `/api/v1/dreams/${id}`);

export const trackEvent = (name: ProductEvent, eventId: string, platform: string) =>
  request<void>('POST', '/api/v1/events', { name, eventId, platform });

export async function checkGoogleProvider(): Promise<void> {
  const { url, key } = publicAuthConfig();
  const response = await fetch(`${url}/auth/v1/settings`, { headers: { apikey: key } });
  if (!response.ok) throw new Error(tr.auth.failed);
  const settings = await response.json();
  if (settings.external?.google !== true) throw new Error(tr.auth.googleDisabled);
}
