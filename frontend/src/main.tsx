import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import { initFirebaseAnalytics } from './lib/firebase'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Production-only, non-blocking Firebase / GA4 website analytics.
void initFirebaseAnalytics()
