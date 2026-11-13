import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { SourceTextModule, SyntheticModule, createContext } from 'node:vm';

const user = { id: 'user-one', email: 'dreamer@example.test', is_anonymous: false, app_metadata: { provider: 'email' }, user_metadata: {} };

async function harness({ configured = true, href = 'http://127.0.0.1:5174/', session = null, overrides = {} } = {}) {
  const calls = [];
  const location = new URL(href);
  location.assign = (url) => calls.push(['navigate', url]);
  const auth = {
    getSession: async () => ({ data: { session }, error: null }),
    getUser: async () => ({ data: { user: session?.user ?? null }, error: null }),
    exchangeCodeForSession: async (code) => { calls.push(['exchange', code]); return { error: null }; },
    signInWithOAuth: async (input) => { calls.push(['oauth', input]); return { data: { url: 'https://provider.example/auth' }, error: null }; },
    linkIdentity: async (input) => { calls.push(['link', input]); return { data: { url: 'https://provider.example/link' }, error: null }; },
    signInWithOtp: async (input) => { calls.push(['otp', input]); return { error: null }; },
    updateUser: async (input, options) => { calls.push(['update', input, options]); return { data: { user: { ...user, user_metadata: input.data ?? {} } }, error: null }; },
    verifyOtp: async (input) => { calls.push(['verify', input]); return { error: null }; },
    signOut: async (input) => { calls.push(['signOut', input]); return { error: null }; },
    onAuthStateChange: (listener) => { calls.push(['watch', listener]); return { data: { subscription: { unsubscribe: () => calls.push(['unsubscribe']) } } }; },
    ...overrides,
  };
  const context = createContext({ URL, URLSearchParams, window: { location, history: { replaceState: (_state, _title, path) => { location.href = new URL(path, location).href; } } } });
  const modules = new Map();
  const sdk = new SyntheticModule(['createClient'], function () {
    this.setExport('createClient', (_url, _key, options) => { calls.push(['client', options]); return { auth }; });
  }, { context });
  async function load(name) {
    if (modules.has(name)) return modules.get(name);
    const source = await readFile(new URL(`../src/${name}.ts`, import.meta.url), 'utf8');
    const module = new SourceTextModule(stripTypeScriptTypes(source), { context, initializeImportMeta(meta) {
      meta.env = configured ? { VITE_SUPABASE_URL: 'https://project.example', VITE_SUPABASE_PUBLISHABLE_KEY: 'public-key' } : {};
    } });
    modules.set(name, module);
    await module.link((specifier) => specifier === '@supabase/supabase-js' ? sdk : load(specifier.slice(2)));
    return module;
  }
  const module = await load('session');
  await module.evaluate();
  return { api: module.namespace, calls, location, auth, profile: modules.get('profile').namespace };
}

const data = (value) => JSON.parse(JSON.stringify(value));

test('missing configuration does not silently create a dev identity or sign in', async () => {
  const { api } = await harness({ configured: false });
  assert.equal(await api.initializeSession(), null);
  assert.equal(await api.getToken(), null);
  await assert.rejects(api.signInGoogle());
});

test('PKCE callback is exchanged once, user verified, auth parameters removed', async () => {
  const { api, calls, location } = await harness({ href: 'http://127.0.0.1:5174/?code=one-use-code&auth=callback&onboarding', session: { user, access_token: 'test-token' } });
  const [first, second] = await Promise.all([api.initializeSession(), api.initializeSession()]);
  assert.equal(first.id, user.id);
  assert.equal(second.id, user.id);
  assert.equal(calls.filter(([kind]) => kind === 'exchange').length, 1);
  assert.equal(location.searchParams.has('code'), false);
  assert.equal(location.searchParams.has('auth'), false);
  assert.equal(location.searchParams.has('onboarding'), true);
});

test('failed callback cannot complete onboarding and is removed from the URL', async () => {
  const { api, location } = await harness({ href: 'http://127.0.0.1:5174/?code=expired&auth=callback', overrides: { exchangeCodeForSession: async () => ({ error: { code: 'flow_state_not_found' } }) } });
  await assert.rejects(api.initializeSession(), { code: 'flow_state_not_found' });
  assert.equal(location.search, '');
});

test('OAuth cancellation does not display provider-controlled error text', async () => {
  const { api, location } = await harness({ href: 'http://127.0.0.1:5174/?error=access_denied&error_description=untrusted-text' });
  await assert.rejects(api.initializeSession(), /Giriş tamamlanmadı/);
  assert.equal(location.search, '');
});

test('Google uses PKCE and requests no additional Google API access', async () => {
  const { api, calls } = await harness();
  await api.signInGoogle();
  assert.equal(calls.find(([kind]) => kind === 'client')[1].auth.flowType, 'pkce');
  const request = calls.find(([kind]) => kind === 'oauth')[1];
  assert.equal(request.provider, 'google');
  assert.equal(request.options.redirectTo, 'http://127.0.0.1:5174/?auth=callback');
  assert.equal(request.options.scopes, undefined);
  assert.equal(calls.at(-1)[0], 'navigate');
});

test('anonymous Google sign-in links the existing identity', async () => {
  const { api, calls } = await harness({ session: { user: { ...user, is_anonymous: true } } });
  await api.signInGoogle();
  assert.equal(calls.filter(([kind]) => kind === 'oauth').length, 0);
  assert.equal(calls.find(([kind]) => kind === 'link')[1].provider, 'google');
});

test('onboarding preferences are attached to the authenticated account', async () => {
  const { api, calls } = await harness();
  const account = await api.saveProfile({ onboarded: true, visibility: 'public' });
  assert.deepEqual(data(account.profile), { onboarded: true, visibility: 'public' });
  assert.deepEqual(data(calls.find(([kind]) => kind === 'update')[1]), { data: { dreamlib: { version: 1, onboarded: true, visibility: 'public' } } });
});

test('untrusted preference metadata defaults to private and cannot represent authorization', async () => {
  const { profile } = await harness();
  for (const metadata of [{}, { dreamlib: null }, { dreamlib: 'public' }, { dreamlib: { visibility: 'friends', onboarded: 'true', role: 'admin' } }]) {
    assert.deepEqual(data(profile.profileFromMetadata(metadata)), { onboarded: false, visibility: 'private' });
  }
});

test('token refresh failures are propagated and sign-out only clears this browser', async () => {
  const { api, calls } = await harness({ overrides: { getSession: async () => ({ data: { session: null }, error: new Error('refresh failed') }) } });
  await assert.rejects(api.getToken(), /refresh failed/);
  await api.signOut();
  assert.deepEqual(data(calls.find(([kind]) => kind === 'signOut')[1]), { scope: 'local' });
});

test('auth listeners unsubscribe and never call SDK functions from the callback', async () => {
  const { api, calls } = await harness();
  let account;
  const stop = api.watchAccount((next) => { account = next; });
  const listener = calls.find(([kind]) => kind === 'watch')[1];
  assert.equal(listener('SIGNED_IN', { user }), undefined);
  assert.equal(account.id, user.id);
  listener('SIGNED_OUT', null);
  assert.equal(account, null);
  stop();
  assert.equal(calls.at(-1)[0], 'unsubscribe');
});
