export type OrchestrationNode = {
  id: string
  name: string
  shortLabel: string
  purpose: string
  input: string
  output: string
  whenUsed: string
  performance: string
  tenantIsolation: string
  safety: string
}

export const ORCHESTRATION_NODES: OrchestrationNode[] = [
  {
    id: 'planner',
    name: 'Planner',
    shortLabel: 'Planner',
    purpose:
      'Selective capability planner. Chooses the minimum set of capabilities required for the question — not every capability on every request.',
    input: 'User question + tenant context',
    output:
      'RoutePlan: planned_routes, requires_synthesis, may_require_write (primary route retained for API compatibility)',
    whenUsed: 'Every agent request starts here.',
    performance:
      'One structured planner LLM call. Single-capability answers skip synthesis and avoid fan-out cost.',
    tenantIsolation: 'Tenant ID / slug are attached before planning; capabilities inherit that context.',
    safety:
      'Bounded structured plan — not an unrestricted autonomous re-planning loop. Unsupported intents map to fallback.',
  },
  {
    id: 'fan-out',
    name: 'Multi-Capability Fan-Out',
    shortLabel: 'Fan-Out',
    purpose:
      'Runs selected independent read capabilities in parallel (RAG, SQL, MCP read) via LangGraph Send fan-out / join.',
    input: 'planned_routes with two or more read capabilities; tool_read_only=true for MCP in composite mode',
    output: 'rag_answer / sql_answer / tool_answer evidence blocks on shared graph state',
    whenUsed: 'Only when the planner selects multiple capabilities for one request.',
    performance:
      'Parallel reads reduce wall-clock vs sequential, but total LLM/tool work still scales with selected capabilities.',
    tenantIsolation:
      'Each branch keeps tenant_id (RAG/SQL) and tenant_slug (MCP). No cross-tenant evidence sharing.',
    safety:
      'Composite MCP fan-out is read-only. Writes never execute during evidence gathering.',
  },
  {
    id: 'synthesis',
    name: 'Grounded Synthesis',
    shortLabel: 'Synthesis',
    purpose:
      'Joins capability evidence into one grounded answer from structured RAG / SQL / MCP outputs — not raw unresolved tool-call history.',
    input: 'Original question + capability evidence blocks (and optional generated SQL metadata)',
    output: 'synthesis_answer used as the user-facing composite response',
    whenUsed: 'Composite requests only. Single-capability fast path bypasses synthesis.',
    performance: 'Adds one synthesis LLM call after fan-out completes.',
    tenantIsolation: 'Synthesizes only evidence produced under the active tenant context.',
    safety:
      'Grounded on returned evidence; does not invent operational facts or execute tools itself.',
  },
  {
    id: 'write-gate',
    name: 'Write Gate',
    shortLabel: 'Write Gate',
    purpose:
      'Optional post-synthesis gate that may propose only allowlisted write actions for human approval.',
    input: 'Question + synthesis/evidence + may_require_write flag',
    output: 'pending_action for create_maintenance_ticket, or no write proposed',
    whenUsed:
      'After synthesis when may_require_write is true. Single-route MCP writes still pause at HITL without this gate.',
    performance: 'Small structured decision call only when a composite write may be needed.',
    tenantIsolation: 'Proposed ticket arguments stay in the active tenant; MCP/host persistence remains tenant-scoped.',
    safety:
      'Allowlisted tools only. Approval is mandatory before any write executes. No autonomous side effects.',
  },
  {
    id: 'a2a-risk',
    name: 'A2A External Risk',
    shortLabel: 'A2A Risk',
    purpose:
      'Company Intelligence + Risk Agent pipeline: public evidence, internal SQL/RAG context, optional A2A follow-up hop.',
    input: 'Commercial risk question + tenant company entities',
    output:
      'a2a_answer + structured risk; medium/high sets pending_action for create_github_issue',
    whenUsed: 'Planner selects external_risk_assessment (Northstar commercial demos).',
    performance:
      'Multi-step LLM + Wikipedia/domain fetches; optional second intelligence hop when evidence is thin.',
    tenantIsolation: 'Entity resolution and SQL evidence are tenant-scoped; refuse unresolved companies.',
    safety:
      'GitHub writes never run inside this node. Medium/high risk pauses at HITL before MCP create_github_issue.',
  },
]
