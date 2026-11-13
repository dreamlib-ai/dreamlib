import { createClient, type User } from '@supabase/supabase-js';
import { profileFromMetadata, type Profile } from './profile';
import { tr } from './strings';

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY;
const supabase = url && key ? createClient(url, key, {
  auth: { flowType: 'pkce', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
}) : null;

export type Account = { id: string; email: string; provider: string; profile: Profile };
const accountOf = (user: User | null): Account | null => user && !user.is_anonymous ? {
  id: user.id, email: user.email ?? '', provider: user.app_metadata.provider ?? 'email', profile: profileFromMetadata(user.user_metadata),
} : null;

function client() {
  if (!supabase) throw new Error(tr.auth.notConfigured);
  return supabase;
}

export function authMessage(error: unknown): string {
  const value = error as { code?: string; status?: number; message?: string } | null;
  if (value?.code === 'over_email_send_rate_limit' || value?.code === 'over_request_rate_limit' || value?.status === 429) return tr.auth.rateLimited;
  if (value?.code === 'identity_already_exists' || value?.code === 'email_exists' || value?.code === 'user_already_exists') return tr.auth.identityConflict;
  if (value?.code === 'provider_disabled' || value?.code === 'unsupported_provider') return tr.auth.googleDisabled;
  if (value?.code === 'otp_expired' || value?.code === 'flow_state_expired' || value?.code === 'flow_state_not_found' || value?.code === 'bad_code_verifier' || value?.code === 'pkce_code_verifier_not_found') return tr.auth.linkExpired;
  if (value?.message && Object.values(tr.auth).some((message) => message === value.message)) return value.message;
  return tr.auth.failed;
}

export function callbackUrl(): string {
  return new URL('/?auth=callback', window.location.origin).href;
}

function clearCallback() {
  const location = new URL(window.location.href);
  for (const name of ['code', 'auth', 'error', 'error_code', 'error_description', 'token_hash', 'type']) location.searchParams.delete(name);
  const fragment = new URLSearchParams(location.hash.slice(1));
  if (['access_token', 'refresh_token', 'error', 'error_description'].some((name) => fragment.has(name))) location.hash = '';
  window.history.replaceState(null, '', location.pathname + location.search + location.hash);
}

let initializing: Promise<Account | null> | undefined;
export function initializeSession(): Promise<Account | null> {
  return initializing ??= (async () => {
    if (!supabase) return null;
    const location = new URL(window.location.href);
    const fragment = new URLSearchParams(location.hash.slice(1));
    if (location.searchParams.has('error') || fragment.has('error')) {
      clearCallback();
      throw new Error(tr.auth.cancelled);
    }
    try {
      const code = location.searchParams.get('code');
      if (code) {
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (error) throw error;
      }
      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;
      if (!data.session) return null;
      const verified = await supabase.auth.getUser();
      if (verified.error) throw verified.error;
      return accountOf(verified.data.user);
    } finally {
      if (location.searchParams.has('code') || location.searchParams.has('auth') || location.searchParams.has('token_hash')) clearCallback();
    }
  })();
}

export function watchAccount(onChange: (account: Account | null) => void): () => void {
  if (!supabase) return () => {};
  const { data } = supabase.auth.onAuthStateChange((event, session) => {
    // Keep this callback synchronous: SDK calls inside it can hold the auth lock.
    if (event !== 'INITIAL_SESSION') onChange(accountOf(session?.user ?? null));
  });
  return () => data.subscription.unsubscribe();
}

export async function getToken(): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session?.access_token ?? null;
}

export async function signInGoogle() {
  const auth = client().auth;
  const current = await auth.getSession();
  if (current.error) throw current.error;
  const credentials = { provider: 'google' as const, options: { redirectTo: callbackUrl(), queryParams: { prompt: 'select_account' }, skipBrowserRedirect: true } };
  const { data, error } = current.data.session?.user.is_anonymous
    ? await auth.linkIdentity(credentials)
    : await auth.signInWithOAuth(credentials);
  if (error) throw error;
  if (!data.url) throw new Error(tr.auth.failed);
  window.location.assign(data.url);
}

export async function saveProfile(profile: Profile): Promise<Account> {
  const { data, error } = await client().auth.updateUser({ data: { dreamlib: { version: 1, ...profile } } });
  if (error) throw error;
  const account = accountOf(data.user);
  if (!account) throw new Error(tr.auth.expired);
  return account;
}

export async function signOut() {
  const { error } = await client().auth.signOut({ scope: 'local' });
  if (error) throw error;
}

export function publicAuthConfig() {
  client();
  return { url, key };
}
