export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/') && url.pathname !== '/healthz') return env.ASSETS.fetch(request);
    const upstream = new URL(url.pathname + url.search, env.API_ORIGIN);
    const headers = new Headers(request.headers);
    headers.delete('host');
    headers.delete('cookie');
    try {
      const response = await fetch(new Request(upstream, { method: request.method, headers, body: request.body, redirect: 'manual', duplex: 'half' }));
      const outgoing = new Headers(response.headers);
      outgoing.set('Cache-Control', 'no-store');
      return new Response(response.body, { status: response.status, statusText: response.statusText, headers: outgoing });
    } catch {
      return Response.json({ error: 'servise şu an ulaşılamıyor' }, { status: 502, headers: { 'Cache-Control': 'no-store' } });
    }
  },
};
