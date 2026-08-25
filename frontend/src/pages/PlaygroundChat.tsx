import type { RefObject } from 'react'

import { IsolationCard } from '../components/IsolationCard'
import { ChatComposer } from '../components/ChatComposer'
import { ChatMessageItem } from '../components/ChatMessage'
import { getExamplePrompts } from '../lib/examplePrompts'
import type { ChatMessage, ExecutionDetails, RetrievalMode } from '../types/agent'

type PlaygroundChatProps = {
  tenantName: string
  messages: ChatMessage[]
  input: string
  retrievalMode: RetrievalMode
  isSending: boolean
  messagesEndRef: RefObject<HTMLDivElement | null>
  onInputChange: (value: string) => void
  onRetrievalModeChange: (mode: RetrievalMode) => void
  onSubmit: () => void
  onSelectPrompt: (prompt: string) => void
  onApprovalResolved: (
    messageId: string,
    approved: boolean,
    answer: string,
    executionDetails?: ExecutionDetails | null,
  ) => void
}

export function PlaygroundChat({
  tenantName,
  messages,
  input,
  retrievalMode,
  isSending,
  messagesEndRef,
  onInputChange,
  onRetrievalModeChange,
  onSubmit,
  onSelectPrompt,
  onApprovalResolved,
}: PlaygroundChatProps) {
  const prompts = getExamplePrompts(tenantName)
  const categories = [...new Set(prompts.map((item) => item.category))]

  return (
    <div className="playground-chat">
      <IsolationCard
        disabled={isSending}
        onTry={() => onSelectPrompt('What does E-100 mean?')}
      />

      <div className="prompt-categories">
        {categories.map((category) => (
          <div key={category} className="prompt-category">
            <h3 className="prompt-category__title">{category}</h3>
            <div className="prompt-category__list">
              {prompts
                .filter((item) => item.category === category)
                .map((item) => (
                  <button
                    key={`${category}-${item.prompt}`}
                    type="button"
                    className="prompt-category__button"
                    disabled={isSending}
                    onClick={() => onSelectPrompt(item.prompt)}
                  >
                    {item.prompt}
                  </button>
                ))}
            </div>
          </div>
        ))}
      </div>

      <div className="chat-panel__messages">
        {messages.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <h2 className="empty-state__title">Ask the agent</h2>
            <p className="empty-state__subtitle">
              Use a suggested prompt or type your own question for {tenantName}. Answers come
              from the live RAG, SQL, MCP, and HITL pipeline.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessageItem
              key={message.id}
              message={message}
              onApprovalResolved={onApprovalResolved}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <ChatComposer
        value={input}
        retrievalMode={retrievalMode}
        disabled={isSending}
        onChange={onInputChange}
        onRetrievalModeChange={onRetrievalModeChange}
        onSubmit={onSubmit}
      />
    </div>
  )
}
