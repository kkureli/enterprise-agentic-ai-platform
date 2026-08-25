import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

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

type RetrievalModeInfoProps = {
  compact?: boolean
}

export function RetrievalModeInfo({ compact }: RetrievalModeInfoProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  useEffect(() => {
    if (!open) {
      return
    }

    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
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

  return (
    <div className={compact ? 'retrieval-info retrieval-info--compact' : 'retrieval-info'} ref={rootRef}>
      <button
        type="button"
        className="retrieval-info__trigger"
        aria-label="Explain retrieval modes"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">ⓘ</span>
      </button>

      {open ? (
        <div
          id={panelId}
          className="retrieval-info__popover"
          role="dialog"
          aria-label="Retrieval mode explanation"
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
      ) : null}
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
