import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Production-only, non-blocking Firebase / GA4 website analytics.
void import('./lib/firebase')
  .then((module) => module.initFirebaseAnalytics())
  .catch(() => {
    // Ignore analytics bootstrap failures.
  })
