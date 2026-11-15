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
import './calm.css';
import App from './App';
import Intro from './Intro';
import Sky from './Sky';

createRoot(document.getElementById('root')!).render(<StrictMode><Sky /><App /><Intro /></StrictMode>);

// S4: installable web app; the service worker only runs in production builds (public/sw.js).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch(() => {}); });
}
