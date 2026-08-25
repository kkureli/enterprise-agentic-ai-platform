type LoadingBlockProps = {
  title: string
  subtitle?: string
  compact?: boolean
}

export function LoadingBlock({ title, subtitle, compact }: LoadingBlockProps) {
  return (
    <div
      className={compact ? 'async-state async-state--compact' : 'async-state'}
      role="status"
      aria-busy="true"
      aria-live="polite"
    >
      <span className="async-state__spinner" aria-hidden="true" />
      <div>
        <p className="async-state__title">{title}</p>
        {subtitle ? <p className="async-state__subtitle">{subtitle}</p> : null}
      </div>
    </div>
  )
}

type ErrorBlockProps = {
  title: string
  message?: string | null
  onRetry?: () => void
  retrying?: boolean
}

export function ErrorBlock({ title, message, onRetry, retrying }: ErrorBlockProps) {
  return (
    <div className="async-state async-state--error" role="alert">
      <div>
        <p className="async-state__title">{title}</p>
        {message ? <p className="async-state__subtitle">{message}</p> : null}
      </div>
      {onRetry ? (
        <button
          type="button"
          className="button button--secondary"
          disabled={retrying}
          onClick={onRetry}
          aria-label="Retry loading"
        >
          {retrying ? 'Retrying…' : 'Retry'}
        </button>
      ) : null}
    </div>
  )
}

type EmptyBlockProps = {
  title: string
  message?: string
}

export function EmptyBlock({ title, message }: EmptyBlockProps) {
  return (
    <div className="async-state async-state--empty">
      <p className="async-state__title">{title}</p>
      {message ? <p className="async-state__subtitle">{message}</p> : null}
    </div>
  )
}
