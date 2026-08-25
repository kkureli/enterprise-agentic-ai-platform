import fs from 'node:fs'
import path from 'node:path'

import { chromium, type Browser, type Page } from '@playwright/test'

import {
  ARTIFACTS_DIR,
  ASSETS_DIR,
  LIVE_DEMO_URL,
  PATHS,
  PROMPTS,
  TENANTS,
  VIEWPORT,
  WORK_DIR,
} from './config.js'
import { readAiCounter, resetAiCounter } from './counters.js'
import { installSyntheticCursor, moveCursor } from './cursor.js'
import {
  composeTenantIsolation,
  fileSizeBytes,
  formatBytes,
  mediaDurationSeconds,
  mp4ToGif,
  mp4ToWebp,
  optimizePng,
  webmToMp4,
} from './media.js'
import {
  composedScreenshot,
  frameAnswerShot,
  frameHeroShot,
  frameTraceShot,
  navigateSidebar,
  openExecutionTrace,
  openPlayground,
  rejectHitl,
  runCompare,
  scrollMainIntoView,
  selectTenant,
  sendPrompt,
  waitForNoTransientUi,
} from './ui.js'

type Mode = 'all' | 'screenshots' | 'preview' | 'video'

function parseArgs(argv: string[]): { mode: Mode; baseUrl: string } {
  let mode: Mode = 'all'
  let baseUrl = LIVE_DEMO_URL
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--screenshots') {
      mode = 'screenshots'
    } else if (arg === '--preview') {
      mode = 'preview'
    } else if (arg === '--video') {
      mode = 'video'
    } else if (arg === '--all') {
      mode = 'all'
    } else if (arg === '--url' && argv[i + 1]) {
      baseUrl = argv[i + 1].replace(/\/$/, '')
      i += 1
    } else if (arg === '--help' || arg === '-h') {
      printHelp()
      process.exit(0)
    }
  }
  return { mode, baseUrl }
}

function printHelp(): void {
  console.log(`Usage: npm run demo:media -- [--all|--screenshots|--preview|--video] [--url URL]

Captures README screenshots, a short demo-preview.gif, and/or a full MP4
from the live Enterprise Agentic AI Playground.

Environment:
  LIVE_DEMO_URL   Override playground URL (default: production SWA)
`)
}

async function pause(page: Page, ms: number): Promise<void> {
  await page.waitForTimeout(ms)
}

async function withBrowser(
  recordVideo: boolean,
  fn: (page: Page, browser: Browser) => Promise<void>,
): Promise<string | null> {
  fs.mkdirSync(WORK_DIR, { recursive: true })
  fs.mkdirSync(ASSETS_DIR, { recursive: true })
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true })

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    recordVideo: recordVideo ? { dir: WORK_DIR, size: VIEWPORT } : undefined,
  })
  const page = await context.newPage()
  await installSyntheticCursor(page)

  let videoPath: string | null = null
  try {
    await fn(page, browser)
  } finally {
    const video = page.video()
    await context.close()
    await browser.close()
    if (recordVideo && video) {
      videoPath = await video.path()
    }
  }
  return videoPath
}

async function snapStaticPages(page: Page): Promise<void> {
  await navigateSidebar(page, 'Evaluation')
  await waitForNoTransientUi(page)
  await scrollMainIntoView(page, '.evaluation-page')
  await page.locator('.eval-disclaimer, .page-header__subtitle').first().waitFor({
    state: 'visible',
  })
  await composedScreenshot(page, PATHS.evaluation)
  optimizePng(PATHS.evaluation)

  await navigateSidebar(page, 'Architecture')
  await waitForNoTransientUi(page)
  const explorer = page.locator('.rag-explorer').first()
  if (await explorer.count()) {
    await explorer.scrollIntoViewIfNeeded()
  } else {
    const heading = page.getByRole('heading', { name: /RAG Pipeline/i }).first()
    if (await heading.count()) {
      await heading.scrollIntoViewIfNeeded()
    } else {
      await scrollMainIntoView(page, '.architecture-page')
    }
  }
  await pause(page, 400)
  await composedScreenshot(page, PATHS.ragArchitecture)
  optimizePng(PATHS.ragArchitecture)
}

/**
 * Core narrative used by --video / --all.
 * Optionally takes README screenshots at safe moments (no extra AI when possible).
 */
async function captureFullDemo(page: Page, takeShots: boolean): Promise<void> {
  const atlasIso = path.join(WORK_DIR, 'atlas-e100.png')
  const borealisIso = path.join(WORK_DIR, 'borealis-e100.png')

  await selectTenant(page, TENANTS.atlas)
  await navigateSidebar(page, 'Playground')
  await moveCursor(page, 320, 160)
  await pause(page, 1000)

  await sendPrompt(page, PROMPTS.e100, 'video:atlas-e100')
  await pause(page, 800)

  if (takeShots) {
    await frameAnswerShot(page)
    await composedScreenshot(page, atlasIso)
    await frameHeroShot(page)
    await composedScreenshot(page, PATHS.hero)
    optimizePng(PATHS.hero)
    await frameTraceShot(page)
    await composedScreenshot(page, PATHS.executionTrace)
    optimizePng(PATHS.executionTrace)
  } else {
    await openExecutionTrace(page)
  }
  await pause(page, 1200)

  await selectTenant(page, TENANTS.borealis)
  await pause(page, 700)
  await sendPrompt(page, PROMPTS.e100, 'video:borealis-e100')
  await pause(page, 800)

  if (takeShots) {
    await frameAnswerShot(page)
    await composedScreenshot(page, borealisIso)
    composeTenantIsolation(atlasIso, borealisIso, PATHS.tenantIsolation)
  } else {
    await openExecutionTrace(page)
  }
  await pause(page, 1200)

  await selectTenant(page, TENANTS.atlas)
  await sendPrompt(page, PROMPTS.sql, 'video:sql')
  await pause(page, 1200)

  await sendPrompt(page, PROMPTS.mcp, 'video:mcp')
  await pause(page, 1200)

  await sendPrompt(page, PROMPTS.hitl, 'video:hitl')
  await rejectHitl(page)
  await pause(page, 1200)

  await navigateSidebar(page, 'Compare Runs')
  await runCompare(page, PROMPTS.compare)
  await pause(page, 1600)

  if (takeShots) {
    await scrollMainIntoView(page, '.compare-answers')
    await composedScreenshot(page, PATHS.compareRuns)
    optimizePng(PATHS.compareRuns)
    await snapStaticPages(page)
  } else {
    await navigateSidebar(page, 'Evaluation')
    await pause(page, 1400)
    await navigateSidebar(page, 'Architecture')
    const explorer = page.getByRole('heading', { name: /RAG Pipeline/i }).first()
    if (await explorer.count()) {
      await explorer.scrollIntoViewIfNeeded()
    }
    await pause(page, 1800)
  }
}

async function captureScreenshotsOnly(page: Page): Promise<void> {
  const atlasIso = path.join(WORK_DIR, 'atlas-e100.png')
  const borealisIso = path.join(WORK_DIR, 'borealis-e100.png')

  await selectTenant(page, TENANTS.atlas)
  await navigateSidebar(page, 'Playground')
  await sendPrompt(page, PROMPTS.e100, 'screenshots:atlas-e100')
  await frameAnswerShot(page)
  await composedScreenshot(page, atlasIso)
  await frameHeroShot(page)
  await composedScreenshot(page, PATHS.hero)
  optimizePng(PATHS.hero)
  await frameTraceShot(page)
  await composedScreenshot(page, PATHS.executionTrace)
  optimizePng(PATHS.executionTrace)

  await selectTenant(page, TENANTS.borealis)
  await sendPrompt(page, PROMPTS.e100, 'screenshots:borealis-e100')
  await frameAnswerShot(page)
  await composedScreenshot(page, borealisIso)
  composeTenantIsolation(atlasIso, borealisIso, PATHS.tenantIsolation)

  await selectTenant(page, TENANTS.atlas)
  await navigateSidebar(page, 'Compare Runs')
  await runCompare(page, PROMPTS.compare)
  await scrollMainIntoView(page, '.compare-page')
  await composedScreenshot(page, PATHS.compareRuns)
  optimizePng(PATHS.compareRuns)

  await snapStaticPages(page)
}

async function capturePreviewSequence(page: Page): Promise<void> {
  await selectTenant(page, TENANTS.atlas)
  await navigateSidebar(page, 'Playground')
  await moveCursor(page, 400, 200)
  await pause(page, 800)
  await sendPrompt(page, PROMPTS.e100, 'preview:atlas-e100')
  await openExecutionTrace(page)
  await pause(page, 1800)
  await selectTenant(page, TENANTS.borealis)
  await pause(page, 700)
  await sendPrompt(page, PROMPTS.e100, 'preview:borealis-e100')
  await openExecutionTrace(page)
  await pause(page, 1800)
}

async function finalizeVideo(rawWebm: string | null, wantPreview: boolean): Promise<void> {
  if (!rawWebm || !fs.existsSync(rawWebm)) {
    throw new Error('Playwright did not produce a video recording')
  }
  fs.copyFileSync(rawWebm, PATHS.videoWebm)
  webmToMp4(PATHS.videoWebm, PATHS.videoMp4)

  if (wantPreview) {
    mp4ToGif(PATHS.videoMp4, PATHS.previewGif, {
      startSec: 0,
      durationSec: 13,
      width: 960,
      fps: 8,
    })
    try {
      mp4ToWebp(PATHS.videoMp4, PATHS.previewWebp, {
        startSec: 0,
        durationSec: 14,
        width: 1100,
        fps: 12,
      })
    } catch (error) {
      console.warn('Optional WebP preview skipped:', error)
    }
  }
}

function writeReport(payload: Record<string, unknown>): void {
  fs.mkdirSync(WORK_DIR, { recursive: true })
  fs.writeFileSync(PATHS.report, JSON.stringify(payload, null, 2))
}

async function main(): Promise<void> {
  const { mode, baseUrl } = parseArgs(process.argv.slice(2))
  console.log(`Demo media · mode=${mode} · url=${baseUrl}`)
  resetAiCounter()

  const wantScreenshots = mode === 'all' || mode === 'screenshots'
  const wantPreview = mode === 'all' || mode === 'preview'
  const wantVideo = mode === 'all' || mode === 'video'

  if (mode === 'screenshots') {
    await withBrowser(false, async (page) => {
      await openPlayground(page, baseUrl)
      await captureScreenshotsOnly(page)
    })
  } else if (mode === 'preview') {
    const raw = await withBrowser(true, async (page) => {
      await openPlayground(page, baseUrl)
      await capturePreviewSequence(page)
    })
    await finalizeVideo(raw, true)
  } else {
    // --video or --all: one recorded pass; optionally snap assets mid-flow.
    const raw = await withBrowser(true, async (page) => {
      await openPlayground(page, baseUrl)
      await captureFullDemo(page, wantScreenshots)
      if (wantVideo && !wantScreenshots) {
        // ending already handled inside captureFullDemo when !takeShots
      }
    })
    await finalizeVideo(raw, wantPreview)
  }

  const ai = readAiCounter()
  const report = {
    mode,
    baseUrl,
    aiRequests: ai.total,
    aiEvents: ai.events,
    assets: {
      hero: formatBytes(fileSizeBytes(PATHS.hero)),
      tenantIsolation: formatBytes(fileSizeBytes(PATHS.tenantIsolation)),
      executionTrace: formatBytes(fileSizeBytes(PATHS.executionTrace)),
      compareRuns: formatBytes(fileSizeBytes(PATHS.compareRuns)),
      evaluation: formatBytes(fileSizeBytes(PATHS.evaluation)),
      ragArchitecture: formatBytes(fileSizeBytes(PATHS.ragArchitecture)),
      previewGif: {
        size: formatBytes(fileSizeBytes(PATHS.previewGif)),
        durationSec: mediaDurationSeconds(PATHS.previewGif) || null,
      },
      videoMp4: {
        size: formatBytes(fileSizeBytes(PATHS.videoMp4)),
        durationSec: mediaDurationSeconds(PATHS.videoMp4) || null,
      },
      videoWebm: formatBytes(fileSizeBytes(PATHS.videoWebm)),
      previewWebp: formatBytes(fileSizeBytes(PATHS.previewWebp)),
    },
  }
  writeReport(report)
  console.log(JSON.stringify(report, null, 2))
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
