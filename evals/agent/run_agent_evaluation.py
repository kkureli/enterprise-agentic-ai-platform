import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid4

from app.agents.graph import agent_graph
from app.core.demo_tenants import DEMO_TENANT_SLUG_BY_NAME, demo_tenant_slug_for_name
from app.db.session import SessionLocal
from app.models import Asset, Tenant
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from sqlalchemy import select

DATASET_PATH = Path(__file__).with_name("golden_dataset.json")
RESULTS_PATH = Path(__file__).resolve().parents[1] / "results" / "agent_evaluation.json"


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def expected_routes_for(case: dict) -> list[str]:
    if "expected_routes" in case:
        return list(case["expected_routes"])
    return [case["expected_route"]]


async def get_default_tenant() -> tuple[UUID, str]:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(Tenant.id, Tenant.name)
                .join(Asset, Asset.tenant_id == Tenant.id)
                .limit(1)
            )
        ).first()

    if row is None:
        raise RuntimeError("No operational tenant found.")

    tenant_id, name = row
    slug = demo_tenant_slug_for_name(name) or f"tenant-{tenant_id}"
    return tenant_id, slug


async def get_tenant_by_slug(slug: str) -> tuple[UUID, str]:
    name = next(
        (tenant_name for tenant_name, value in DEMO_TENANT_SLUG_BY_NAME.items() if value == slug),
        None,
    )
    if name is None:
        raise RuntimeError(f"Unknown demo tenant slug: {slug}")

    async with SessionLocal() as session:
        tenant_id = await session.scalar(select(Tenant.id).where(Tenant.name == name))
    if tenant_id is None:
        raise RuntimeError(f"Demo tenant not seeded: {name}")
    return tenant_id, slug


async def preflight_required_tenants(dataset: list[dict]) -> None:
    """Fail fast before spending AI budget if required demo tenants are missing."""

    required_slugs: set[str] = set()
    for case in dataset:
        if case.get("tenant_slug"):
            required_slugs.add(case["tenant_slug"])

    # Default eval path needs at least one seeded operational tenant; prefer Atlas.
    required_names = {"Atlas Manufacturing"}
    for slug in required_slugs:
        name = next(
            (tenant_name for tenant_name, value in DEMO_TENANT_SLUG_BY_NAME.items() if value == slug),
            None,
        )
        if name:
            required_names.add(name)

    async with SessionLocal() as session:
        existing = {
            name
            for name in (
                await session.scalars(select(Tenant.name).where(Tenant.name.in_(required_names)))
            ).all()
        }

    missing = sorted(required_names - existing)
    if missing:
        raise RuntimeError(
            "Demo tenants required by the evaluation dataset are not seeded: "
            f"{', '.join(missing)}. "
            "Seed locally first (do not seed production from the evaluator):\n"
            "  cd backend && PYTHONPATH=. uv run --env-file .env.development "
            "python scripts/seed_demo_playground.py"
        )


def capability_success(result: dict, route: str) -> bool:
    if route == "knowledge":
        return bool((result.get("rag_answer") or "").strip())
    if route == "sql":
        return bool((result.get("sql_answer") or "").strip())
    if route == "tool":
        return bool((result.get("tool_answer") or "").strip())
    return True


def synthesis_fact_coverage(answer: str, required_facts: list[str] | None) -> float | None:
    if not required_facts:
        return None
    if not answer:
        return 0.0
    lowered = answer.lower()
    hits = sum(1 for fact in required_facts if fact.lower() in lowered)
    return hits / len(required_facts)


async def evaluate_agent() -> None:
    dataset = load_dataset()
    await preflight_required_tenants(dataset)
    default_tenant_id, default_slug = await get_default_tenant()

    evaluation_results = []
    execution_success = 0
    route_correct = 0
    approval_correct = 0
    fully_passed = 0

    required_recall_scores: list[float] = []
    exact_set_hits = 0
    composite_cases = 0
    unnecessary_rates: list[float] = []
    per_cap_success_scores: list[float] = []
    synthesis_coverage_scores: list[float] = []
    tenant_correct = 0
    tenant_cases = 0

    for case in dataset:
        thread_id = str(uuid4())
        expected_routes = expected_routes_for(case)
        tenant_slug = case.get("tenant_slug") or default_slug
        if case.get("tenant_slug"):
            tenant_id, tenant_slug = await get_tenant_by_slug(case["tenant_slug"])
        else:
            tenant_id = default_tenant_id

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [CallbackHandler()],
            "run_name": "agent-evaluation",
            "metadata": {
                "eval_case_id": case["id"],
                "tenant_id": str(tenant_id),
                "tenant_slug": tenant_slug,
                "thread_id": thread_id,
            },
        }

        try:
            result = await agent_graph.ainvoke(
                {
                    "tenant_id": tenant_id,
                    "tenant_slug": tenant_slug,
                    "query": case["question"],
                    "retrieval_mode": "standard",
                },
                config=config,
            )

            execution_success += 1
            actual_routes = list(result.get("planned_routes") or [result["route"]])
            actual_route = result["route"]
            actual_approval = bool(result.get("__interrupt__"))

            route_passed = actual_routes == expected_routes
            # Backward-compatible primary route check for legacy reporting.
            primary_route_passed = actual_route == case["expected_route"] or route_passed
            approval_passed = actual_approval == case["expected_approval"]
            answer = result.get("final_answer") or result.get("tool_answer") or ""
            if actual_approval:
                answer = result.get("tool_answer") or answer
            answer_present = bool(str(answer).strip())

            expected_set = set(expected_routes)
            actual_set = set(actual_routes)
            required_recall = (
                len(expected_set & actual_set) / len(expected_set) if expected_set else 1.0
            )
            required_recall_scores.append(required_recall)
            exact_set = actual_routes == expected_routes
            exact_set_hits += int(exact_set)
            if len(expected_routes) > 1:
                composite_cases += 1

            extras = actual_set - expected_set
            unnecessary_rates.append(
                len(extras) / len(actual_set) if actual_set else 0.0
            )

            cap_scores = [
                float(capability_success(result, route))
                for route in expected_routes
                if route != "unsupported"
            ]
            if cap_scores:
                per_cap_success_scores.append(sum(cap_scores) / len(cap_scores))

            coverage = synthesis_fact_coverage(str(answer), case.get("required_facts"))
            if coverage is not None and len(expected_routes) > 1:
                synthesis_coverage_scores.append(coverage)

            tenant_ok = True
            if case.get("tenant_slug"):
                tenant_cases += 1
                tools = (result.get("execution_details") or {}).get("tools") or {}
                if tools.get("tenant_slug") and tools.get("tenant_slug") != tenant_slug:
                    tenant_ok = False
                tenant_correct += int(tenant_ok)

            passed = (
                route_passed
                and approval_passed
                and answer_present
                and tenant_ok
                and required_recall == 1.0
            )

            route_correct += int(primary_route_passed)
            approval_correct += int(approval_passed)
            fully_passed += int(passed)

            evaluation_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected_route": case["expected_route"],
                    "expected_routes": expected_routes,
                    "actual_route": actual_route,
                    "actual_routes": actual_routes,
                    "expected_approval": case["expected_approval"],
                    "actual_approval": actual_approval,
                    "answer": answer,
                    "route_passed": route_passed,
                    "approval_passed": approval_passed,
                    "answer_present": answer_present,
                    "required_capability_recall": required_recall,
                    "exact_capability_set": exact_set,
                    "passed": passed,
                    "error": None,
                }
            )

            symbol = "✅" if passed else "❌"
            print(
                f"{symbol} {case['id']}: routes={actual_routes}, approval={actual_approval}"
            )
            if not passed:
                print(
                    f"   expected routes={expected_routes}, "
                    f"approval={case['expected_approval']}"
                )

        except Exception as exc:  # noqa: BLE001
            evaluation_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected_route": case["expected_route"],
                    "expected_routes": expected_routes_for(case),
                    "actual_route": None,
                    "actual_routes": None,
                    "expected_approval": case["expected_approval"],
                    "actual_approval": None,
                    "answer": None,
                    "route_passed": False,
                    "approval_passed": False,
                    "answer_present": False,
                    "required_capability_recall": 0.0,
                    "exact_capability_set": False,
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"💥 {case['id']}: {type(exc).__name__}: {exc}")

    total = len(dataset)
    metrics = {
        "route_accuracy": route_correct / total if total else 0,
        "approval_accuracy": approval_correct / total if total else 0,
        "execution_success_rate": execution_success / total if total else 0,
        "end_to_end_pass_rate": fully_passed / total if total else 0,
        "required_capability_recall": (
            sum(required_recall_scores) / len(required_recall_scores)
            if required_recall_scores
            else 0
        ),
        "exact_capability_set_accuracy": exact_set_hits / total if total else 0,
        "unnecessary_capability_rate": (
            sum(unnecessary_rates) / len(unnecessary_rates) if unnecessary_rates else 0
        ),
        "per_capability_execution_success": (
            sum(per_cap_success_scores) / len(per_cap_success_scores)
            if per_cap_success_scores
            else 0
        ),
        "synthesis_required_fact_coverage": (
            sum(synthesis_coverage_scores) / len(synthesis_coverage_scores)
            if synthesis_coverage_scores
            else None
        ),
        "tenant_correctness": (
            tenant_correct / tenant_cases if tenant_cases else None
        ),
        "composite_cases": composite_cases,
    }

    print()
    for key, value in metrics.items():
        if value is None:
            continue
        if isinstance(value, float):
            print(f"{key}: {value:.2%}" if value <= 1 else f"{key}: {value}")
        else:
            print(f"{key}: {value}")

    output = {
        "total_cases": total,
        "metrics": metrics,
        "results": evaluation_results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {RESULTS_PATH}")
    get_client().flush()


if __name__ == "__main__":
    asyncio.run(evaluate_agent())
