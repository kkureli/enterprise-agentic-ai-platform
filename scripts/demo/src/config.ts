import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
export const REPO_ROOT = path.resolve(here, '../../..')

export const LIVE_DEMO_URL =
  process.env.LIVE_DEMO_URL?.replace(/\/$/, '') ??
  'https://white-river-0fe20910f.7.azurestaticapps.net'

export const VIEWPORT = { width: 1440, height: 900 } as const

export const ASSETS_DIR = path.join(REPO_ROOT, 'docs/assets')
export const ARTIFACTS_DIR = path.join(REPO_ROOT, 'artifacts/demo')
export const WORK_DIR = path.join(ARTIFACTS_DIR, '.work')

export const PATHS = {
  hero: path.join(ASSETS_DIR, 'hero-playground.png'),
  tenantIsolation: path.join(ASSETS_DIR, 'tenant-isolation.png'),
  executionTrace: path.join(ASSETS_DIR, 'execution-trace.png'),
  compareRuns: path.join(ASSETS_DIR, 'compare-runs.png'),
  evaluation: path.join(ASSETS_DIR, 'evaluation.png'),
  ragArchitecture: path.join(ASSETS_DIR, 'rag-architecture.png'),
  previewGif: path.join(ASSETS_DIR, 'demo-preview.gif'),
  previewWebp: path.join(ARTIFACTS_DIR, 'demo-preview.webp'),
  videoMp4: path.join(ARTIFACTS_DIR, 'enterprise-agentic-ai-demo.mp4'),
  videoWebm: path.join(ARTIFACTS_DIR, 'enterprise-agentic-ai-demo.webm'),
  aiCounter: path.join(WORK_DIR, 'ai-request-count.json'),
  report: path.join(WORK_DIR, 'last-run-report.json'),
} as const

export const PROMPTS = {
  e100: 'What does E-100 mean?',
  sql: 'Which assets currently have warnings?',
  mcp: 'What is the current operational status of MACHINE-42?',
  hitl:
    'Create a high-priority maintenance ticket for MACHINE-42 because of hydraulic pressure loss.',
  compare: 'What does E-100 mean?',
} as const

export const TENANTS = {
  atlas: 'Atlas Manufacturing',
  borealis: 'Borealis Cold Chain',
} as const

/** Soft ceiling — abort if live AI calls exceed this in one media run. */
export const MAX_AI_REQUESTS = 12

export const AGENT_TIMEOUT_MS = 180_000
export const PAGE_SETTLE_MS = 600
