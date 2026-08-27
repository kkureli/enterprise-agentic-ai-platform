# GitHub MCP write tool (Sprint 5)

`create_github_issue` opens a **real** GitHub Issue in the configured repo
(default: `kkureli/enterprise-agentic-ai-platform`).

## Auth

Set on the **backend** host (passed through to the MCP stdio process):

```bash
GITHUB_TOKEN=ghp_...   # classic or fine-grained PAT with Issues: write
GITHUB_REPO=kkureli/enterprise-agentic-ai-platform
GITHUB_API_BASE=https://api.github.com
```

## HITL

The host must **not** call this tool until after human approval.
`execute_approved_action(..., tool_name=create_github_issue)`:

1. Creates internal `risk_escalations` row
2. Checks `external_action_links` for `dedupe_key` (skip duplicate GitHub create)
3. Calls MCP `create_github_issue`
4. Stores audit/link metadata (+ `risk_escalation_id`)

## SQL audit columns

`external_action_links`: provider, external_id, external_url, action_type,
status, dedupe_key, optional internal_ticket_id / company_query.
