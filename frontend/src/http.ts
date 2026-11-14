// One HTTP door for the API: auth header, timeout, and errors with machine codes (docs/api.md).
import { getToken } from './session';
import { tr } from './strings';

/** Machine codes from docs/api.md (S2); the message is for people and may change. */
export type ErrorCode = 'invalid_request' | 'auth_required' | 'auth_invalid' | 'not_found' | 'conflict' | 'revision_conflict'
  | 'job_busy' | 'too_large' | 'unsupported_media' | 'unreadable' | 'daily_limit' | 'rate_limited' | 'upstream_failed'
  | 'service_off' | 'internal';
export class ApiError extends Error {
  status: number;
  code: ErrorCode;
  constructor(status:number,message:string,code:ErrorCode='internal') { super(message); this.status=status; this.code=code; }
}

export async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
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
