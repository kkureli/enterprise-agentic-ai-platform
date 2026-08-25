import fs from 'node:fs'
import path from 'node:path'

import { MAX_AI_REQUESTS, PATHS, WORK_DIR } from './config.js'

export type AiCounter = {
  total: number
  events: Array<{ at: string; label: string }>
}

function emptyCounter(): AiCounter {
  return { total: 0, events: [] }
}

export function resetAiCounter(): void {
  fs.mkdirSync(WORK_DIR, { recursive: true })
  fs.writeFileSync(PATHS.aiCounter, JSON.stringify(emptyCounter(), null, 2))
}

export function readAiCounter(): AiCounter {
  if (!fs.existsSync(PATHS.aiCounter)) {
    return emptyCounter()
  }
  return JSON.parse(fs.readFileSync(PATHS.aiCounter, 'utf8')) as AiCounter
}

export function recordAiRequest(label: string): number {
  const counter = readAiCounter()
  counter.total += 1
  counter.events.push({ at: new Date().toISOString(), label })
  fs.mkdirSync(path.dirname(PATHS.aiCounter), { recursive: true })
  fs.writeFileSync(PATHS.aiCounter, JSON.stringify(counter, null, 2))
  if (counter.total > MAX_AI_REQUESTS) {
    throw new Error(
      `Live AI safety stop: exceeded MAX_AI_REQUESTS=${MAX_AI_REQUESTS} (label=${label})`,
    )
  }
  return counter.total
}
