/**
 * Privacy-conscious Firebase Analytics.
 *
 * - Production only
 * - Standard GA4 site metrics + virtual UI screen page_views
 * - Screen events send ONLY allowlisted section ids / titles
 * - Never sends prompts, answers, SQL, traces, tenant IDs, or other app content
 */

import type { Analytics } from 'firebase/analytics'

type FirebaseWebConfig = {
  apiKey: string
  authDomain: string
  projectId: string
  storageBucket: string
  messagingSenderId: string
  appId: string
  measurementId: string
}

/** Allowlisted playground sections only — never free-form user content. */
const SCREEN_TITLES = {
  playground: 'Playground',
  documents: 'Documents',
  operations: 'Operations',
  compare: 'Compare Runs',
  evaluation: 'Evaluation',
  status: 'System Status',
  architecture: 'Architecture',
} as const

type AnalyticsScreen = keyof typeof SCREEN_TITLES

let analyticsInstance: Analytics | null = null
let initStarted = false
let pendingScreen: AnalyticsScreen | null = null

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

function isAnalyticsScreen(value: string): value is AnalyticsScreen {
  return value in SCREEN_TITLES
}

async function emitScreenView(screen: AnalyticsScreen): Promise<void> {
  if (!analyticsInstance) {
    return
  }

  const { logEvent } = await import('firebase/analytics')
  const path = `/ui/${screen}`
  const origin = typeof window !== 'undefined' ? window.location.origin : ''

  logEvent(analyticsInstance, 'page_view', {
    page_title: SCREEN_TITLES[screen],
    page_path: path,
    page_location: origin ? `${origin}${path}` : path,
  })
}

/**
 * Initialize Firebase Analytics when supported. Safe to call without awaiting.
 * Automatic first page_view is disabled so SPA section views are not double-counted.
 */
export async function initFirebaseAnalytics(): Promise<void> {
  if (initStarted || !import.meta.env.PROD) {
    return
  }
  initStarted = true

  try {
    const config = readFirebaseConfig()
    if (!config) {
      return
    }

    const { initializeApp } = await import('firebase/app')
    const { initializeAnalytics, isSupported } = await import('firebase/analytics')

    if (!(await isSupported())) {
      return
    }

    const app = initializeApp(config)
    analyticsInstance = initializeAnalytics(app, {
      config: {
        // SPA owns virtual page_view events for allowlisted UI sections.
        send_page_view: false,
      },
    })

    if (pendingScreen) {
      const screen = pendingScreen
      pendingScreen = null
      await emitScreenView(screen)
    }
  } catch {
    analyticsInstance = null
  }
}

/**
 * Record a playground section view. Accepts only allowlisted section ids.
 * Safe no-op when Analytics is unavailable.
 */
export function logScreenView(screen: string): void {
  try {
    if (!import.meta.env.PROD || !isAnalyticsScreen(screen)) {
      return
    }

    if (!analyticsInstance) {
      pendingScreen = screen
      void initFirebaseAnalytics()
      return
    }

    void emitScreenView(screen)
  } catch {
    // Analytics must never break the playground.
  }
}
