import type { PromptCategory } from '../types/playground'

export type ExamplePrompt = {
  category: PromptCategory
  prompt: string
}

const PROMPTS_BY_TENANT: Record<string, ExamplePrompt[]> = {
  'Atlas Manufacturing': [
    { category: 'Knowledge / RAG', prompt: 'What does error code AX-4317 mean?' },
    { category: 'Knowledge / RAG', prompt: 'What does E-100 mean?' },
    { category: 'Structured Data / SQL', prompt: 'Which assets currently have warnings?' },
    {
      category: 'Structured Data / SQL',
      prompt: 'How many maintenance records does MACHINE-42 have?',
    },
    {
      category: 'Live Tools / MCP',
      prompt: 'What is the current operational status of MACHINE-42?',
    },
    {
      category: 'Human Approval / HITL',
      prompt:
        'Create a high-priority maintenance ticket for MACHINE-42 because of hydraulic pressure loss.',
    },
    { category: 'Tenant Isolation', prompt: 'What does E-100 mean?' },
  ],
  'Borealis Cold Chain': [
    { category: 'Knowledge / RAG', prompt: 'What does CL-209 mean?' },
    { category: 'Knowledge / RAG', prompt: 'What does E-100 mean?' },
    {
      category: 'Structured Data / SQL',
      prompt: 'Which refrigeration assets currently have warnings?',
    },
    {
      category: 'Structured Data / SQL',
      prompt: 'Show maintenance history for CHILLER-12.',
    },
    {
      category: 'Live Tools / MCP',
      prompt: 'What is the current operational status of CHILLER-12?',
    },
    {
      category: 'Human Approval / HITL',
      prompt:
        'Create a high-priority maintenance ticket for CHILLER-12 because of low refrigerant suction pressure.',
    },
    { category: 'Tenant Isolation', prompt: 'What does E-100 mean?' },
  ],
  'Helios Energy Services': [
    { category: 'Knowledge / RAG', prompt: 'What does WT-302 mean?' },
    { category: 'Knowledge / RAG', prompt: 'What does E-100 mean?' },
    {
      category: 'Structured Data / SQL',
      prompt: 'Which assets are currently in maintenance?',
    },
    {
      category: 'Structured Data / SQL',
      prompt: 'Show maintenance history for TURBINE-08.',
    },
    {
      category: 'Live Tools / MCP',
      prompt: 'What is the current operational status of TURBINE-08?',
    },
    {
      category: 'Human Approval / HITL',
      prompt:
        'Create a high-priority maintenance ticket for TURBINE-08 because of yaw motor overload.',
    },
    { category: 'Tenant Isolation', prompt: 'What does E-100 mean?' },
  ],
}

export function getExamplePrompts(tenantName: string): ExamplePrompt[] {
  return PROMPTS_BY_TENANT[tenantName] ?? PROMPTS_BY_TENANT['Atlas Manufacturing']
}
