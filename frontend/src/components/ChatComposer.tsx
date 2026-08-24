import { useRef } from 'react'

import type { RetrievalMode } from '../types/agent'

type ChatComposerProps = {
  value: string
  retrievalMode: RetrievalMode
  disabled: boolean
  onChange: (value: string) => void
  onRetrievalModeChange: (mode: RetrievalMode) => void
  onSubmit: () => void
}

export function ChatComposer({
  value,
  retrievalMode,
  disabled,
  onChange,
  onRetrievalModeChange,
  onSubmit,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!disabled && value.trim()) {
        onSubmit()
      }
    }
  }

  return (
    <div className="composer">
      <div className="composer__toolbar">
        <label className="composer__mode-label" htmlFor="retrieval-mode">
          Retrieval
        </label>
        <select
          id="retrieval-mode"
          className="composer__mode-select"
          value={retrievalMode}
          disabled={disabled}
          onChange={(event) => onRetrievalModeChange(event.target.value as RetrievalMode)}
        >
          <option value="standard">Standard</option>
          <option value="advanced">Advanced</option>
        </select>
      </div>

      <div className="composer__input-row">
        <textarea
          ref={textareaRef}
          className="composer__textarea"
          rows={3}
          placeholder="Ask about policies, operational data, asset status, or maintenance actions…"
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="button button--primary composer__send"
          disabled={disabled || !value.trim()}
          onClick={onSubmit}
        >
          Send
        </button>
      </div>
      <p className="composer__hint">Enter to send · Shift+Enter for newline</p>
    </div>
  )
}
