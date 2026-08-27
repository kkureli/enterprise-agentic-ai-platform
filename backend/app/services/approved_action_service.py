from typing import Any
from uuid import UUID

from app.services.external_action_link_service import (
    create_external_action_link,
    find_external_action_link,
)
from app.services.maintenance_ticket_service import (
    create_maintenance_ticket,
)
from app.services.mcp_client import call_maintenance_tool

APPROVED_WRITE_ACTIONS = {
    "create_maintenance_ticket",
    "create_github_issue",
}


class UnsupportedApprovedActionError(ValueError):
    pass


def _mcp_structured_content(result: Any) -> dict[str, Any]:
    content = getattr(result, "structured_content", None)
    if isinstance(content, dict):
        return content
    # Some MCP clients return content list payloads.
    raw = getattr(result, "content", None)
    if isinstance(raw, list) and raw:
        first = raw[0]
        text = getattr(first, "text", None)
        if isinstance(text, str) and text.strip().startswith("{"):
            import json

            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
    raise ValueError("MCP tool did not return structured content.")


async def _execute_create_github_issue(
    *,
    tenant_id: UUID,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    title = str(arguments.get("title") or "").strip()
    body = str(arguments.get("body") or "").strip()
    tenant_slug = str(arguments.get("tenant_slug") or "").strip()
    dedupe_key = str(arguments.get("dedupe_key") or "").strip()
    company_query = arguments.get("company_query")
    labels = arguments.get("labels")
    internal_ticket_id = arguments.get("internal_ticket_id")

    if not title or not body:
        raise ValueError("create_github_issue requires title and body.")
    if not tenant_slug:
        raise ValueError("create_github_issue requires tenant_slug.")
    if not dedupe_key:
        raise ValueError("create_github_issue requires dedupe_key for audit/dedupe.")

    existing = await find_external_action_link(
        tenant_id=tenant_id,
        dedupe_key=dedupe_key,
    )
    if existing is not None:
        return {
            "tool_name": "create_github_issue",
            "deduplicated": True,
            "provider": existing.provider,
            "external_id": existing.external_id,
            "external_url": existing.external_url,
            "status": existing.status,
            "dedupe_key": existing.dedupe_key,
            "internal_ticket_id": (
                str(existing.internal_ticket_id) if existing.internal_ticket_id else None
            ),
            "company_query": existing.company_query,
        }

    mcp_args: dict[str, Any] = {
        "title": title,
        "body": body,
        "tenant_slug": tenant_slug,
        "dedupe_key": dedupe_key,
    }
    if isinstance(labels, list):
        mcp_args["labels"] = labels

    mcp_result = await call_maintenance_tool(
        "create_github_issue",
        mcp_args,
        tenant_slug=tenant_slug,
    )
    payload = _mcp_structured_content(mcp_result)

    ticket_uuid: UUID | None = None
    if internal_ticket_id:
        ticket_uuid = UUID(str(internal_ticket_id))

    link = await create_external_action_link(
        tenant_id=tenant_id,
        provider="github",
        external_id=str(payload.get("id") or payload.get("number")),
        external_url=str(payload["html_url"]),
        action_type="create_issue",
        status=str(payload.get("state") or "open"),
        dedupe_key=dedupe_key,
        internal_ticket_id=ticket_uuid,
        company_query=str(company_query) if company_query else None,
    )

    return {
        "tool_name": "create_github_issue",
        "deduplicated": False,
        "provider": "github",
        "external_id": link.external_id,
        "external_url": link.external_url,
        "status": link.status,
        "dedupe_key": link.dedupe_key,
        "issue_number": payload.get("number"),
        "repository": payload.get("repository"),
        "internal_ticket_id": str(ticket_uuid) if ticket_uuid else None,
        "company_query": link.company_query,
    }


async def execute_approved_action(
    tenant_id: UUID,
    pending_action: dict[str, Any],
) -> dict[str, Any]:
    tool_name = pending_action.get("tool_name")
    arguments = pending_action.get("arguments")

    if tool_name not in APPROVED_WRITE_ACTIONS:
        raise UnsupportedApprovedActionError(f"Approved action is not allowed: {tool_name}")

    if not isinstance(arguments, dict):
        raise ValueError("Pending action arguments are invalid.")

    if tool_name == "create_maintenance_ticket":
        ticket = await create_maintenance_ticket(
            tenant_id=tenant_id,
            asset_code=arguments["asset_code"],
            issue=arguments["issue"],
            priority=arguments["priority"],
        )

        return {
            "tool_name": tool_name,
            "ticket_id": str(ticket.id),
            "asset_id": str(ticket.asset_id),
            "issue": ticket.issue,
            "priority": ticket.priority,
            "status": ticket.status,
        }

    if tool_name == "create_github_issue":
        return await _execute_create_github_issue(
            tenant_id=tenant_id,
            arguments=arguments,
        )

    raise UnsupportedApprovedActionError(f"No executor implemented for action: {tool_name}")
