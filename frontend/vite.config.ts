import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

declare const process: { env: Record<string, string | undefined> }; // Node's, without pulling in @types/node

// In dev the browser talks to Vite, which forwards /api to the API (no CORS needed).
// In Docker (`npm run db -- app`) the API is another container and the source is a Windows bind
// mount, where file events do not arrive: DREAMLIB_API_PROXY and DREAMLIB_POLL cover both.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly instead of silently moving to another port
    proxy: { '/api': process.env.DREAMLIB_API_PROXY || 'http://127.0.0.1:8080' },
    watch: process.env.DREAMLIB_POLL === '1' ? { usePolling: true, interval: 300 } : undefined,
  },
});
