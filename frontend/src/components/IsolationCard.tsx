type IsolationCardProps = {
  onTry: () => void
  disabled?: boolean
}

export function IsolationCard({ onTry, disabled }: IsolationCardProps) {
  return (
    <section className="isolation-card">
      <div className="isolation-card__content">
        <p className="isolation-card__eyebrow">Tenant Isolation Demo</p>
        <h3 className="isolation-card__title">
          Same code: <code className="isolation-card__code">E-100</code>
        </h3>
        <p className="isolation-card__body">
          Different tenant-grounded meaning. Switch tenants and run the same query.
        </p>
      </div>
      <button
        type="button"
        className="button button--primary"
        disabled={disabled}
        onClick={onTry}
        aria-label="Ask about E-100"
      >
        Ask about E-100
      </button>
    </section>
  )
}
