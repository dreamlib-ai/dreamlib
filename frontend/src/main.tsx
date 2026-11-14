import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './fonts.css';
import './theme.css';
import './app.css';
import './workspace.css';
import './atmosphere.css';
import './editorial.css';
import './brain.css';
import './magazine.css';
import App from './App';

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);

// S4: installable web app; the service worker only runs in production builds (public/sw.js).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch(() => {}); });
}
