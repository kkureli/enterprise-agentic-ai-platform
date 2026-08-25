import type { Locator, Page } from '@playwright/test'

import { AGENT_TIMEOUT_MS, PAGE_SETTLE_MS, PROMPTS, TENANTS } from './config.js'
import { recordAiRequest } from './counters.js'
import {
  clickWithCursor,
  hideSyntheticCursor,
  moveCursor,
  showSyntheticCursor,
} from './cursor.js'

export async function waitForNoTransientUi(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const busy = document.querySelector(
      '.async-state[aria-busy="true"], .chat-panel__messages[aria-busy="true"]',
    )
    const spinner = document.querySelector('.async-state__spinner')
    const running = document.querySelector('.composer__status')
    const loadingDots = document.querySelector('.chat-message__loading')
    return !busy && !spinner && !running && !loadingDots
  }, { timeout: 120_000 })
  await page.waitForTimeout(PAGE_SETTLE_MS)
}

export async function openPlayground(page: Page, baseUrl: string): Promise<void> {
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60_000 })
  await page.locator('#demo-tenant').waitFor({ state: 'visible', timeout: 120_000 })
  await page.waitForFunction(() => {
    const select = document.querySelector('#demo-tenant') as HTMLSelectElement | null
    return Boolean(select && !select.disabled && select.options.length > 1)
  }, { timeout: 180_000 })
  await waitForNoTransientUi(page)
}

export async function selectTenant(page: Page, tenantName: string): Promise<void> {
  const select = page.locator('#demo-tenant')
  await select.waitFor({ state: 'visible' })
  const option = select.locator('option', { hasText: tenantName })
  const value = await option.getAttribute('value')
  if (!value) {
    throw new Error(`Tenant option not found: ${tenantName}`)
  }
  await select.selectOption(value)
  await page.waitForTimeout(PAGE_SETTLE_MS)
  await waitForNoTransientUi(page)
}

export async function navigateSidebar(page: Page, label: string): Promise<void> {
  const button = page.locator('nav.sidebar').getByRole('button', { name: label, exact: true })
  await button.waitFor({ state: 'visible', timeout: 30_000 })
  const box = await button.boundingBox()
  if (box) {
    await moveCursor(page, box.x + box.width / 2, box.y + box.height / 2)
    await page.waitForTimeout(100)
  }
  await button.click({ force: true })

  if (label === 'Playground') {
    await page.locator('.composer__textarea, .playground-chat').first().waitFor({
      state: 'visible',
      timeout: 60_000,
    })
  } else {
    await page.getByRole('heading', { name: label, exact: true }).waitFor({
      state: 'visible',
      timeout: 60_000,
    })
  }

  // Best-effort active state check; heading visibility is the source of truth.
  await page
    .waitForFunction(
      (name) => {
        const active = document.querySelector('nav.sidebar button[aria-current="page"]')
        const text = (active?.textContent ?? '').replace(/\s+/g, ' ').trim()
        return text === name
      },
      label,
      { timeout: 5_000 },
    )
    .catch(() => undefined)

  await waitForNoTransientUi(page)
}

export async function dismissOverlays(page: Page): Promise<void> {
  // Close any open info popovers that might cover the shot.
  await page.keyboard.press('Escape').catch(() => undefined)
  await page.waitForTimeout(150)
}

async function waitForAssistantSettled(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const dots = document.querySelector('.chat-message__loading')
    const running = document.querySelector('.composer__status')
    return !dots && !running
  }, { timeout: AGENT_TIMEOUT_MS })

  const error = page.locator('.chat-message--assistant .chat-message__error-label')
  if (await error.count()) {
    const text = await page.locator('.chat-message--assistant .chat-message__text').last().innerText()
    if (/429|rate limit|budget/i.test(text)) {
      throw new Error(`Rate limited / budget blocked: ${text.slice(0, 200)}`)
    }
    throw new Error(`Assistant returned error: ${text.slice(0, 240)}`)
  }

  await page
    .locator('.chat-message--assistant .chat-message__text')
    .last()
    .waitFor({ state: 'visible', timeout: 10_000 })
}

export async function sendPrompt(
  page: Page,
  prompt: string,
  label: string,
): Promise<void> {
  recordAiRequest(label)
  await page.locator('.composer__textarea').fill(prompt)
  await clickWithCursor(page, 'button.composer__send')
  await waitForAssistantSettled(page)
  await waitForNoTransientUi(page)
}

export async function openExecutionTrace(page: Page): Promise<Locator> {
  const details = page.locator('details.execution-trace').last()
  await details.waitFor({ state: 'visible', timeout: 30_000 })
  const open = await details.getAttribute('open')
  if (open == null) {
    await details.locator('summary').click()
  }
  await details.locator('.execution-trace__body').waitFor({ state: 'visible', timeout: 10_000 })
  await page.waitForTimeout(PAGE_SETTLE_MS)
  return details
}

/** Frame Playground so header + full assistant answer + Execution Trace summary share the viewport. */
export async function frameHeroShot(page: Page): Promise<void> {
  const answer = page.locator('.chat-message--assistant').last()
  await answer.waitFor({ state: 'visible' })
  // Keep the details collapsed so the answer stays readable; summary still advertises the trace.
  await page.evaluate(() => {
    document.querySelectorAll('details.execution-trace[open]').forEach((node) => {
      node.removeAttribute('open')
    })
  })
  await page.locator('details.execution-trace').last().locator('summary').waitFor({
    state: 'visible',
  })
  await page.evaluate(() => {
    const node = document.querySelector('.chat-panel__messages .chat-message--user:last-of-type')
    ;(node ?? document.querySelector('.chat-panel__messages .chat-message--assistant:last-of-type'))
      ?.scrollIntoView({ block: 'start', inline: 'nearest' })
  })
  await page.waitForTimeout(PAGE_SETTLE_MS)
}

/** Frame for tenant-isolation collage: emphasize Q&A bubbles. */
export async function frameAnswerShot(page: Page): Promise<void> {
  const thread = page.locator('.chat-panel__messages')
  await thread.waitFor({ state: 'visible' })
  const answer = page.locator('.chat-message--assistant .chat-message__text').last()
  await answer.waitFor({ state: 'visible' })
  await answer.scrollIntoViewIfNeeded()
  await page.waitForTimeout(PAGE_SETTLE_MS)
}

/** Frame Execution Trace body (route, retrieval, sources, cost). */
export async function frameTraceShot(page: Page): Promise<void> {
  const details = await openExecutionTrace(page)
  await details.locator('.execution-trace__body').scrollIntoViewIfNeeded()
  await page.waitForTimeout(PAGE_SETTLE_MS)
}

export async function composedScreenshot(
  page: Page,
  targetPath: string,
  options?: { hideCursor?: boolean; clip?: { x: number; y: number; width: number; height: number } },
): Promise<void> {
  await dismissOverlays(page)
  await waitForNoTransientUi(page)
  if (options?.hideCursor !== false) {
    await hideSyntheticCursor(page)
  }
  await page.screenshot({
    path: targetPath,
    type: 'png',
    animations: 'disabled',
    clip: options?.clip,
  })
  await showSyntheticCursor(page)
}

export async function scrollMainIntoView(page: Page, selector: string): Promise<void> {
  const loc = page.locator(selector).first()
  await loc.waitFor({ state: 'visible', timeout: 30_000 })
  await loc.scrollIntoViewIfNeeded()
  await page.waitForTimeout(PAGE_SETTLE_MS)
}

export async function runCompare(page: Page, question = PROMPTS.compare): Promise<void> {
  // Compare triggers two agent executions.
  recordAiRequest('compare:standard')
  recordAiRequest('compare:advanced')
  await page.getByRole('heading', { name: 'Compare Runs', exact: true }).waitFor({
    state: 'visible',
    timeout: 60_000,
  })
  const field = page.locator('#compare-question')
  await field.waitFor({ state: 'visible', timeout: 60_000 })
  await field.fill(question)
  await clickWithCursor(page, 'button.button--primary:has-text("Compare Standard vs Advanced")')
  await page.waitForSelector('.compare-answers, .page-error, .async-state__spinner', {
    timeout: 30_000,
  })
  await page.waitForFunction(() => !document.querySelector('.async-state__spinner'), {
    timeout: AGENT_TIMEOUT_MS,
  })
  const err = page.locator('.page-error')
  if (await err.count()) {
    throw new Error(`Compare failed: ${(await err.first().innerText()).slice(0, 240)}`)
  }
  await page.locator('.compare-answers').waitFor({ state: 'visible', timeout: AGENT_TIMEOUT_MS })
  await page.locator('.compare-answers').scrollIntoViewIfNeeded()
  await waitForNoTransientUi(page)
}

export async function rejectHitl(page: Page): Promise<void> {
  const card = page.locator('.approval-card')
  await card.waitFor({ state: 'visible', timeout: AGENT_TIMEOUT_MS })
  await card.scrollIntoViewIfNeeded()
  await clickWithCursor(page, '.approval-card button:has-text("Reject")')
  await page.waitForSelector('.chat-message__approval-status', { timeout: AGENT_TIMEOUT_MS })
  await waitForNoTransientUi(page)
}

export { PROMPTS, TENANTS }
