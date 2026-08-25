/**
 * Privacy-conscious Firebase Analytics bootstrap.
 *
 * Collects only standard Firebase / GA4 website telemetry (visits, traffic,
 * approximate geo, active users). Never sends AI prompts, answers, SQL,
 * documents, execution traces, tenant IDs, or other application content.
 *
 * Navigation in this app is React state only (URL does not change), so we rely
 * on automatic collection for site visits and intentionally do NOT emit custom
 * per-screen page_view events.
 */

type FirebaseWebConfig = {
  apiKey: string
  authDomain: string
  projectId: string
  storageBucket: string
  messagingSenderId: string
  appId: string
  measurementId: string
}

function readFirebaseConfig(): FirebaseWebConfig | null {
  const apiKey = import.meta.env.VITE_FIREBASE_API_KEY?.trim()
  const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.trim()
  const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim()
  const storageBucket = import.meta.env.VITE_FIREBASE_STORAGE_BUCKET?.trim()
  const messagingSenderId = import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID?.trim()
  const appId = import.meta.env.VITE_FIREBASE_APP_ID?.trim()
  const measurementId = import.meta.env.VITE_FIREBASE_MEASUREMENT_ID?.trim()

  if (
    !apiKey ||
    !authDomain ||
    !projectId ||
    !storageBucket ||
    !messagingSenderId ||
    !appId ||
    !measurementId
  ) {
    return null
  }

  return {
    apiKey,
    authDomain,
    projectId,
    storageBucket,
    messagingSenderId,
    appId,
    measurementId,
  }
}

/**
 * Initialize Firebase Analytics when supported. Safe to call without awaiting.
 * Never throws into the application; never blocks rendering.
 */
export async function initFirebaseAnalytics(): Promise<void> {
  try {
    if (!import.meta.env.PROD) {
      return
    }

    const config = readFirebaseConfig()
    if (!config) {
      return
    }

    const { initializeApp } = await import('firebase/app')
    const { getAnalytics, isSupported } = await import('firebase/analytics')

    if (!(await isSupported())) {
      return
    }

    const app = initializeApp(config)
    getAnalytics(app)
  } catch {
    // Analytics must never break the playground.
  }
}
