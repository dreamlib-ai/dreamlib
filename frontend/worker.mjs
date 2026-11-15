const SHARED = /^\/m\/([A-Za-z0-9_-]{8,32})\/?$/;
const escape = text => String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

/** G6: a shared magazine's page is the app itself, with link-preview tags for apps that do not run scripts. */
async function sharedPage(request, env, slug) {
  const page = await env.ASSETS.fetch(new Request(new URL('/', request.url), request));
  let title = '';
  try {
    const answer = await fetch(new URL(`/api/v1/m/${slug}`, env.API_ORIGIN), { headers: { Accept: 'application/json' } });
    if (answer.ok) title = (await answer.json()).spec?.cover?.title ?? '';
  } catch { /* no preview tags; the page still works */ }
  const html = await page.text();
  const origin = new URL(request.url).origin;
  const tags = title ? [
    ['og:type', 'article'], ['og:site_name', 'Dreamlib'], ['og:title', title], ['og:description', "Dreamlib'de bir rüya dergisi"],
    ['og:url', `${origin}/m/${slug}`], ['og:image', `${origin}/api/v1/m/${slug}/cover`],
  ].map(([k, v]) => `<meta property="${k}" content="${escape(v)}" />`).join('') + '<meta name="twitter:card" content="summary_large_image" />'
    + `<meta name="robots" content="noindex" />` : '<meta name="robots" content="noindex" />';
  const body = html.replace('</head>', `${tags}</head>`).replace(/<title>[^<]*<\/title>/, title ? `<title>${escape(title)} · Dreamlib</title>` : '$&');
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' } });
}

// a shared magazine's pictures, kept at the edge so repeated reads do not reach the API (and its bandwidth)
const PICTURE = /^\/api\/v1\/m\/[A-Za-z0-9_-]{8,32}\/(p\/\d+|cover)$/;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const shared = url.pathname.match(SHARED);
    if (shared && request.method === 'GET') return sharedPage(request, env, shared[1]);
    if (!url.pathname.startsWith('/api/') && url.pathname !== '/healthz') return env.ASSETS.fetch(request);
    const picture = request.method === 'GET' && PICTURE.test(url.pathname);
    const key = new Request(url.toString(), { method: 'GET' });
    if (picture) {
      const kept = await caches.default.match(key);
      if (kept) return kept;
    }
    const upstream = new URL(url.pathname + url.search, env.API_ORIGIN);
    const headers = new Headers(request.headers);
    headers.delete('host');
    headers.delete('cookie');
    try {
      const response = await fetch(new Request(upstream, { method: request.method, headers, body: request.body, redirect: 'manual', duplex: 'half' }));
      const outgoing = new Headers(response.headers);
      // G6: a shared magazine's pictures may be kept for as long as the API says; every other answer never is
      const shared = request.method === 'GET' && url.pathname.startsWith('/api/v1/m/') && response.ok;
      if (!shared || !outgoing.get('Cache-Control')?.startsWith('public')) outgoing.set('Cache-Control', 'no-store');
      const answer = new Response(response.body, { status: response.status, statusText: response.statusText, headers: outgoing });
      if (picture && response.status === 200 && outgoing.get('Cache-Control')?.startsWith('public')) {
        ctx.waitUntil(caches.default.put(key, answer.clone()));
      }
      return answer;
    } catch {
      return Response.json({ error: 'servise şu an ulaşılamıyor' }, { status: 502, headers: { 'Cache-Control': 'no-store' } });
    }
  },
};
