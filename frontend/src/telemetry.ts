import { trackEvent } from './api';

export type ProductEvent = 'session_open' | 'record_started' | 'transcript_ready' | 'analysis_ready' | 'booklet_ready' | 'dream_saved' | 'feedback_helpful' | 'feedback_unhelpful';
export function track(name: ProductEvent, eventId: string) {
  const platform = /iPhone|iPad|iPod/.test(navigator.userAgent) ? 'ios' : /Android/.test(navigator.userAgent) ? 'android' : 'desktop';
  void trackEvent(name, eventId, platform).catch(() => { /* Measurement never blocks the dream. */ });
}
export function sessionEvent(owner: string) {
  try {
    const key = `dreamlib:visit:${owner}:${new Date().toISOString().slice(0, 10)}`;
    let id = sessionStorage.getItem(key);
    if (id) return;
    id = crypto.randomUUID(); sessionStorage.setItem(key, id); track('session_open', id);
  } catch { /* Storage can be denied in private mode. */ }
}
