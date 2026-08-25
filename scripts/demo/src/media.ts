import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

import { WORK_DIR } from './config.js'

function which(bin: string): string | null {
  try {
    return execFileSync('which', [bin], { encoding: 'utf8' }).trim() || null
  } catch {
    return null
  }
}

export function requireBin(bin: string): string {
  const found = which(bin)
  if (!found) {
    throw new Error(`Required binary not found on PATH: ${bin}`)
  }
  return found
}

export function optimizePng(filePath: string): void {
  const magick = which('magick') ?? which('convert')
  if (!magick) {
    return
  }
  const tmp = `${filePath}.opt.png`
  // Mild compression; keep text readable.
  execFileSync(
    magick,
    [filePath, '-strip', '-define', 'png:compression-level=9', tmp],
    { stdio: 'inherit' },
  )
  fs.renameSync(tmp, filePath)
}

export function composeTenantIsolation(
  atlasPath: string,
  borealisPath: string,
  outPath: string,
): void {
  const magick = requireBin('magick')
  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  const captionAtlas = path.join(WORK_DIR, 'caption-atlas.png')
  const captionBorealis = path.join(WORK_DIR, 'caption-borealis.png')
  const left = path.join(WORK_DIR, 'iso-left.png')
  const right = path.join(WORK_DIR, 'iso-right.png')

  execFileSync(
    magick,
    [
      '-size',
      '700x48',
      'xc:#0f172a',
      '-fill',
      '#f8fafc',
      '-font',
      'Helvetica-Bold',
      '-pointsize',
      '22',
      '-gravity',
      'center',
      '-annotate',
      '0',
      'Atlas Manufacturing · “What does E-100 mean?”',
      captionAtlas,
    ],
    { stdio: 'inherit' },
  )
  execFileSync(
    magick,
    [
      '-size',
      '700x48',
      'xc:#0f172a',
      '-fill',
      '#f8fafc',
      '-font',
      'Helvetica-Bold',
      '-pointsize',
      '22',
      '-gravity',
      'center',
      '-annotate',
      '0',
      'Borealis Cold Chain · “What does E-100 mean?”',
      captionBorealis,
    ],
    { stdio: 'inherit' },
  )

  execFileSync(
    magick,
    [atlasPath, '-resize', '700x', captionAtlas, '+swap', '-append', left],
    { stdio: 'inherit' },
  )
  execFileSync(
    magick,
    [borealisPath, '-resize', '700x', captionBorealis, '+swap', '-append', right],
    { stdio: 'inherit' },
  )

  execFileSync(
    magick,
    [
      left,
      right,
      '+smush',
      '24',
      '-background',
      '#e2e8f0',
      '-gravity',
      'center',
      '-extent',
      '%[fx:w+48]x%[fx:h+64]',
      '-fill',
      '#0f172a',
      '-font',
      'Helvetica',
      '-pointsize',
      '18',
      '-gravity',
      'north',
      '-annotate',
      '+0+16',
      'Same question · different tenant-grounded answers (live RAG)',
      outPath,
    ],
    { stdio: 'inherit' },
  )

  optimizePng(outPath)
}

export function webmToMp4(webmPath: string, mp4Path: string): void {
  const ffmpeg = requireBin('ffmpeg')
  fs.mkdirSync(path.dirname(mp4Path), { recursive: true })
  execFileSync(
    ffmpeg,
    [
      '-y',
      '-i',
      webmPath,
      '-c:v',
      'libx264',
      '-pix_fmt',
      'yuv420p',
      '-movflags',
      '+faststart',
      '-an',
      mp4Path,
    ],
    { stdio: 'inherit' },
  )
}

export function mp4ToGif(
  mp4Path: string,
  gifPath: string,
  options?: { startSec?: number; durationSec?: number; width?: number; fps?: number },
): void {
  const ffmpeg = requireBin('ffmpeg')
  const start = options?.startSec ?? 0
  const duration = options?.durationSec ?? 14
  const width = options?.width ?? 1200
  const fps = options?.fps ?? 10
  const palette = path.join(WORK_DIR, 'palette.png')
  fs.mkdirSync(WORK_DIR, { recursive: true })
  fs.mkdirSync(path.dirname(gifPath), { recursive: true })

  const trim = ['-ss', String(start), '-t', String(duration)]
  const vf = `fps=${fps},scale=${width}:-1:flags=lanczos`

  execFileSync(
    ffmpeg,
    [
      '-y',
      ...trim,
      '-i',
      mp4Path,
      '-vf',
      `${vf},palettegen=stats_mode=diff`,
      '-update',
      '1',
      palette,
    ],
    { stdio: 'inherit' },
  )
  execFileSync(
    ffmpeg,
    [
      '-y',
      ...trim,
      '-i',
      mp4Path,
      '-i',
      palette,
      '-lavfi',
      `${vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5`,
      gifPath,
    ],
    { stdio: 'inherit' },
  )
}

export function mp4ToWebp(
  mp4Path: string,
  webpPath: string,
  options?: { startSec?: number; durationSec?: number; width?: number; fps?: number },
): void {
  const ffmpeg = requireBin('ffmpeg')
  const start = options?.startSec ?? 0
  const duration = options?.durationSec ?? 14
  const width = options?.width ?? 1200
  const fps = options?.fps ?? 12
  fs.mkdirSync(path.dirname(webpPath), { recursive: true })
  execFileSync(
    ffmpeg,
    [
      '-y',
      '-ss',
      String(start),
      '-t',
      String(duration),
      '-i',
      mp4Path,
      '-vf',
      `fps=${fps},scale=${width}:-1:flags=lanczos`,
      '-loop',
      '0',
      '-an',
      webpPath,
    ],
    { stdio: 'inherit' },
  )
}

export function mediaDurationSeconds(filePath: string): number {
  const ffprobe = which('ffprobe')
  if (!ffprobe) {
    return 0
  }
  const out = execFileSync(
    ffprobe,
    ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nk=1:nw=1', filePath],
    { encoding: 'utf8' },
  ).trim()
  return Number.parseFloat(out) || 0
}

export function fileSizeBytes(filePath: string): number {
  if (!fs.existsSync(filePath)) {
    return 0
  }
  return fs.statSync(filePath).size
}

export function formatBytes(n: number): string {
  if (n < 1024) {
    return `${n} B`
  }
  if (n < 1024 * 1024) {
    return `${(n / 1024).toFixed(1)} KB`
  }
  return `${(n / (1024 * 1024)).toFixed(2)} MB`
}
