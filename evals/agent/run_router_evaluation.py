"""Router/planner evaluation — supports single-route and composite expected sets."""

import asyncio
import json
from pathlib import Path

from app.agents.router import planner_node

DATASET_PATH = Path(__file__).with_name("golden_dataset.json")


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def expected_routes_for(case: dict) -> list[str]:
    if "expected_routes" in case:
        return list(case["expected_routes"])
    return [case["expected_route"]]


async def evaluate_router() -> None:
    dataset = load_dataset()
    passed_count = 0
    failures: list[dict] = []

    for case in dataset:
        result = await planner_node(
            {
                "query": case["question"],
                "tenant_id": None,  # type: ignore[typeddict-item]
            }
        )
        actual_routes = list(result.get("planned_routes") or [result["route"]])
        expected_routes = expected_routes_for(case)
        passed = actual_routes == expected_routes
        passed_count += int(passed)
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {case['id']}: expected={expected_routes} actual={actual_routes}")
        if not passed:
            failures.append(
                {
                    "id": case["id"],
                    "expected_routes": expected_routes,
                    "actual_routes": actual_routes,
                }
            )

    total = len(dataset)
    print(f"\nPlanner accuracy: {passed_count}/{total} ({passed_count / total if total else 0:.2%})")
    if failures:
        print("Failures:")
        for failure in failures:
            print(
                f"  {failure['id']}: {failure['expected_routes']} -> {failure['actual_routes']}"
            )


if __name__ == "__main__":
    asyncio.run(evaluate_router())
