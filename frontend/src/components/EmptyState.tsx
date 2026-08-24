type EmptyStateProps = {
  onSelectPrompt: (prompt: string) => void
}

const EXAMPLE_PROMPTS = [
  'What does error code AX-4317 mean?',
  'How many maintenance records does MACHINE-42 have?',
  'What is the current operational status of MACHINE-42?',
  'Create a high-priority maintenance ticket for MACHINE-42 because of hydraulic pressure loss.',
]

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h2 className="empty-state__title">Enterprise Operations Assistant</h2>
      <p className="empty-state__subtitle">
        Ask about policies, query operational data, check asset status, or request maintenance
        actions that require human approval.
      </p>
      <div className="empty-state__prompts">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="empty-state__prompt"
            onClick={() => onSelectPrompt(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}
