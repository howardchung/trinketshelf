import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { loadAllCatalogData } from './data/catalog';

const rootEl = document.getElementById('root')!;

loadAllCatalogData()
  .then(async () => {
    const { default: App } = await import('./App');
    createRoot(rootEl).render(
      <StrictMode>
        <App />
      </StrictMode>
    );
  })
  .catch((err) => {
    rootEl.innerHTML = `<div style="padding:2rem;font-family:sans-serif;text-align:center"><h2>Failed to load TrinketShelf catalog</h2><p>${String(err)}</p></div>`;
  });

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Service worker registration optional in non-HTTPS dev environments
    });
  });
}
