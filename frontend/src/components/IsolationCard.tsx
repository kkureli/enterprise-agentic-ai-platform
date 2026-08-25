type IsolationCardProps = {
  onTry: () => void
  disabled?: boolean
}

export function IsolationCard({ onTry, disabled }: IsolationCardProps) {
  return (
    <section className="isolation-card">
      <div>
        <h3 className="isolation-card__title">Try tenant isolation</h3>
        <p className="isolation-card__body">
          The same error code <strong>E-100</strong> exists in all three demo tenants with
          different meanings. Switch tenants and run the same query to verify tenant-scoped
          retrieval.
        </p>
        <p className="isolation-card__prompt">What does E-100 mean?</p>
      </div>
      <button
        type="button"
        className="button button--primary"
        disabled={disabled}
        onClick={onTry}
      >
        Ask about E-100
      </button>
    </section>
  )
}
