import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev the browser talks to Vite, which forwards /api to the API (no CORS needed).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly instead of silently moving to another port
    proxy: { '/api': 'http://127.0.0.1:8080' },
  },
});
