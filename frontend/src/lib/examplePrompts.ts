import type { PromptCategory } from '../types/playground'

export type ExamplePrompt = {
  category: PromptCategory
  label: string
  prompt: string
}

const PROMPTS_BY_TENANT: Record<string, ExamplePrompt[]> = {
  'Atlas Manufacturing': [
    { category: 'Knowledge / RAG', label: 'AX-4317', prompt: 'What does error code AX-4317 mean?' },
    { category: 'Knowledge / RAG', label: 'E-100', prompt: 'What does E-100 mean?' },
    {
      category: 'Structured Data / SQL',
      label: 'Assets with warnings',
      prompt: 'Which assets currently have warnings?',
    },
    {
      category: 'Structured Data / SQL',
      label: 'MACHINE-42 maintenance history',
      prompt: 'How many maintenance records does MACHINE-42 have?',
    },
    {
      category: 'Live Tools / MCP',
      label: 'MACHINE-42 status',
      prompt: 'What is the current operational status of MACHINE-42?',
    },
    {
      category: 'Human Approval / HITL',
      label: 'Create MACHINE-42 ticket',
      prompt:
        'Create a high-priority maintenance ticket for MACHINE-42 because of hydraulic pressure loss.',
    },
  ],
  'Borealis Cold Chain': [
    { category: 'Knowledge / RAG', label: 'CL-209', prompt: 'What does CL-209 mean?' },
    { category: 'Knowledge / RAG', label: 'E-100', prompt: 'What does E-100 mean?' },
    {
      category: 'Structured Data / SQL',
      label: 'Assets with warnings',
      prompt: 'Which refrigeration assets currently have warnings?',
    },
    {
      category: 'Structured Data / SQL',
      label: 'CHILLER-12 maintenance history',
      prompt: 'Show maintenance history for CHILLER-12.',
    },
    {
      category: 'Live Tools / MCP',
      label: 'CHILLER-12 status',
      prompt: 'What is the current operational status of CHILLER-12?',
    },
    {
      category: 'Human Approval / HITL',
      label: 'Create CHILLER-12 ticket',
      prompt:
        'Create a high-priority maintenance ticket for CHILLER-12 because of low refrigerant suction pressure.',
    },
  ],
  'Helios Energy Services': [
    { category: 'Knowledge / RAG', label: 'WT-302', prompt: 'What does WT-302 mean?' },
    { category: 'Knowledge / RAG', label: 'E-100', prompt: 'What does E-100 mean?' },
    {
      category: 'Structured Data / SQL',
      label: 'Assets in maintenance',
      prompt: 'Which assets are currently in maintenance?',
    },
    {
      category: 'Structured Data / SQL',
      label: 'TURBINE-08 maintenance history',
      prompt: 'Show maintenance history for TURBINE-08.',
    },
    {
      category: 'Live Tools / MCP',
      label: 'TURBINE-08 status',
      prompt: 'What is the current operational status of TURBINE-08?',
    },
    {
      category: 'Human Approval / HITL',
      label: 'Create TURBINE-08 ticket',
      prompt:
        'Create a high-priority maintenance ticket for TURBINE-08 because of yaw motor overload.',
    },
  ],
}

export function getExamplePrompts(tenantName: string): ExamplePrompt[] {
  return PROMPTS_BY_TENANT[tenantName] ?? PROMPTS_BY_TENANT['Atlas Manufacturing']
}
