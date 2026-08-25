import type { Page } from '@playwright/test'

import { PAGE_SETTLE_MS, TENANTS } from './config.js'

const CURSOR_ID = '__demo_media_cursor__'

export async function installSyntheticCursor(page: Page): Promise<void> {
  await page.addInitScript((id) => {
    const ensure = () => {
      if (document.getElementById(id)) {
        return
      }
      const el = document.createElement('div')
      el.id = id
      el.setAttribute('aria-hidden', 'true')
      Object.assign(el.style, {
        position: 'fixed',
        left: '0px',
        top: '0px',
        width: '18px',
        height: '18px',
        borderRadius: '50%',
        border: '2px solid #0f172a',
        background: 'rgba(14, 165, 233, 0.35)',
        boxShadow: '0 0 0 3px rgba(14, 165, 233, 0.2)',
        pointerEvents: 'none',
        zIndex: '2147483647',
        transform: 'translate(-50%, -50%)',
        transition: 'left 80ms linear, top 80ms linear',
      })
      document.documentElement.appendChild(el)
    }
    ensure()
    const observer = new MutationObserver(ensure)
    observer.observe(document.documentElement, { childList: true, subtree: true })
  }, CURSOR_ID)

  await page.evaluate((id) => {
    if (document.getElementById(id)) {
      return
    }
    const el = document.createElement('div')
    el.id = id
    el.setAttribute('aria-hidden', 'true')
    Object.assign(el.style, {
      position: 'fixed',
      left: '0px',
      top: '0px',
      width: '18px',
      height: '18px',
      borderRadius: '50%',
      border: '2px solid #0f172a',
      background: 'rgba(14, 165, 233, 0.35)',
      boxShadow: '0 0 0 3px rgba(14, 165, 233, 0.2)',
      pointerEvents: 'none',
      zIndex: '2147483647',
      transform: 'translate(-50%, -50%)',
      transition: 'left 80ms linear, top 80ms linear',
    })
    document.documentElement.appendChild(el)
  }, CURSOR_ID)
}

export async function moveCursor(page: Page, x: number, y: number, steps = 12): Promise<void> {
  await page.mouse.move(x, y, { steps })
  await page.evaluate(
    ({ id, x: cx, y: cy }) => {
      const el = document.getElementById(id)
      if (el) {
        el.style.left = `${cx}px`
        el.style.top = `${cy}px`
      }
    },
    { id: CURSOR_ID, x, y },
  )
}

export async function clickWithCursor(
  page: Page,
  selector: string,
  options?: { timeout?: number },
): Promise<void> {
  const locator = page.locator(selector).first()
  await locator.waitFor({ state: 'visible', timeout: options?.timeout ?? 30_000 })
  const box = await locator.boundingBox()
  if (!box) {
    await locator.click()
    return
  }
  const x = box.x + box.width / 2
  const y = box.y + box.height / 2
  await moveCursor(page, x, y)
  await page.waitForTimeout(120)
  await page.mouse.click(x, y)
  await page.waitForTimeout(PAGE_SETTLE_MS / 2)
}

export async function hideSyntheticCursor(page: Page): Promise<void> {
  await page.evaluate((id) => {
    const el = document.getElementById(id)
    if (el) {
      el.style.display = 'none'
    }
  }, CURSOR_ID)
}

export async function showSyntheticCursor(page: Page): Promise<void> {
  await page.evaluate((id) => {
    const el = document.getElementById(id)
    if (el) {
      el.style.display = 'block'
    }
  }, CURSOR_ID)
}

export type TenantKey = keyof typeof TENANTS
