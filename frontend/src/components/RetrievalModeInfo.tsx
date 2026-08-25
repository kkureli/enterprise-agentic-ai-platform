import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import {
  ADVANCED_CAPABILITIES,
  ADVANCED_PIPELINE,
  ADVANCED_SUMMARY,
  RETRIEVAL_TRADEOFF_NOTE,
  STANDARD_CAPABILITIES,
  STANDARD_PIPELINE,
  STANDARD_SUMMARY,
  type PipelineStep,
} from '../lib/retrievalModes'

const POPOVER_GAP = 8
const VIEWPORT_PAD = 12
const POPOVER_MAX_WIDTH = 576

function PipelineFlow({ steps, label }: { steps: PipelineStep[]; label: string }) {
  return (
    <div className="retrieval-pipeline" aria-label={label}>
      {steps.map((step, index) => (
        <div key={`${label}-${step}`} className="retrieval-pipeline__item">
          <span className="retrieval-pipeline__step">{step}</span>
          {index < steps.length - 1 ? (
            <span className="retrieval-pipeline__arrow" aria-hidden="true">
              ↓
            </span>
          ) : null}
        </div>
      ))}
    </div>
  )
}

function ModePanel({
  title,
  summary,
  capabilities,
  pipeline,
  pipelineLabel,
}: {
  title: string
  summary: string
  capabilities: readonly string[]
  pipeline: PipelineStep[]
  pipelineLabel: string
}) {
  return (
    <section className="retrieval-info__mode">
      <h4 className="retrieval-info__mode-title">{title}</h4>
      <p className="retrieval-info__mode-summary">{summary}</p>
      <ul className="retrieval-info__list">
        {capabilities.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p className="retrieval-info__pipeline-label">Pipeline</p>
      <PipelineFlow steps={pipeline} label={pipelineLabel} />
    </section>
  )
}

function positionPopover(trigger: DOMRect, panel: HTMLElement): CSSProperties {
  const width = Math.min(POPOVER_MAX_WIDTH, window.innerWidth - VIEWPORT_PAD * 2)
  const height = panel.offsetHeight
  const spaceBelow = window.innerHeight - trigger.bottom - VIEWPORT_PAD
  const spaceAbove = trigger.top - VIEWPORT_PAD
  const placeAbove = spaceBelow < height + POPOVER_GAP && spaceAbove > spaceBelow

  let top = placeAbove ? trigger.top - height - POPOVER_GAP : trigger.bottom + POPOVER_GAP
  top = Math.max(VIEWPORT_PAD, Math.min(top, window.innerHeight - height - VIEWPORT_PAD))

  // Prefer aligning to the trigger's left edge; clamp into the viewport.
  let left = trigger.left
  left = Math.max(VIEWPORT_PAD, Math.min(left, window.innerWidth - width - VIEWPORT_PAD))

  return {
    position: 'fixed',
    top,
    left,
    width,
    right: 'auto',
  }
}

type RetrievalModeInfoProps = {
  compact?: boolean
}

export function RetrievalModeInfo({ compact }: RetrievalModeInfoProps) {
  const [open, setOpen] = useState(false)
  const [style, setStyle] = useState<CSSProperties | undefined>()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  useLayoutEffect(() => {
    if (!open) {
      setStyle(undefined)
      return
    }

    if (!triggerRef.current || !panelRef.current) {
      return
    }

    function updatePosition() {
      if (!triggerRef.current || !panelRef.current) {
        return
      }
      setStyle(positionPopover(triggerRef.current.getBoundingClientRect(), panelRef.current))
    }

    updatePosition()

    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) {
      return
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node
      if (rootRef.current?.contains(target) || panelRef.current?.contains(target)) {
        return
      }
      setOpen(false)
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  const popover = open ? (
    <div
      ref={panelRef}
      id={panelId}
      className="retrieval-info__popover"
      role="dialog"
      aria-label="Retrieval mode explanation"
      style={{ ...style, visibility: style ? 'visible' : 'hidden' }}
    >
      <div className="retrieval-info__modes">
        <ModePanel
          title="Standard"
          summary={STANDARD_SUMMARY}
          capabilities={STANDARD_CAPABILITIES}
          pipeline={STANDARD_PIPELINE}
          pipelineLabel="Standard retrieval pipeline"
        />
        <ModePanel
          title="Advanced"
          summary={ADVANCED_SUMMARY}
          capabilities={ADVANCED_CAPABILITIES}
          pipeline={ADVANCED_PIPELINE}
          pipelineLabel="Advanced retrieval pipeline"
        />
      </div>
      <p className="retrieval-info__note">{RETRIEVAL_TRADEOFF_NOTE}</p>
    </div>
  ) : null

  return (
    <div className={compact ? 'retrieval-info retrieval-info--compact' : 'retrieval-info'} ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="retrieval-info__trigger"
        aria-label="Explain retrieval modes"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">ⓘ</span>
      </button>

      {popover ? createPortal(popover, document.body) : null}
    </div>
  )
}

export function RetrievalPipelineInline({
  mode,
}: {
  mode: 'standard' | 'advanced'
}): ReactNode {
  const steps = mode === 'advanced' ? ADVANCED_PIPELINE : STANDARD_PIPELINE
  return (
    <PipelineFlow
      steps={steps}
      label={mode === 'advanced' ? 'Advanced retrieval pipeline' : 'Standard retrieval pipeline'}
    />
  )
}
