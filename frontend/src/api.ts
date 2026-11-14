// The only place the web app talks to the API. Calls and wire types come from ./generated/api.ts, which
// scripts/gen_client.py writes from the backend's OpenAPI schema (S3); this file narrows the free-text
// fields the app knows more about and keeps the app's own call shapes.
import { getToken, publicAuthConfig } from './session';
import { tr } from './strings';
import type { ProductEvent } from './telemetry';
import type { AvatarSpec, PresetId } from './avatar';
import * as g from './generated/api';
import { ApiError } from './http';

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

export const listDreams = () => g.listDreams().then((r) => r.dreams.map(asDream));

export const deleteDream = (id: string) => g.deleteDream(id);

export const trackEvent = (name: ProductEvent, eventId: string, platform: g.EventIn['platform']) =>
  g.event({ name, eventId, platform });

export async function checkGoogleProvider(): Promise<void> {
  const { url, key } = publicAuthConfig();
  const response = await fetch(`${url}/auth/v1/settings`, { headers: { apikey: key } });
  if (!response.ok) throw new Error(tr.auth.failed);
  const settings = await response.json();
  if (settings.external?.google !== true) throw new Error(tr.auth.googleDisabled);
}
