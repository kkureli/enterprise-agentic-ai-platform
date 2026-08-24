import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.agents.router import router_node

DATASET_PATH = Path(__file__).with_name("golden_dataset.json")


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as file:
        return json.load(file)


async def evaluate_router() -> None:
    dataset = load_dataset()

    correct = 0
    results = []

    for case in dataset:
        result = await router_node(
            {
                "tenant_id": uuid4(),
                "query": case["question"],
                "retrieval_mode": "standard",
            }
        )

        actual_route = result["route"]
        expected_route = case["expected_route"]
        passed = actual_route == expected_route

        if passed:
            correct += 1

        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_route": expected_route,
                "actual_route": actual_route,
                "passed": passed,
            }
        )

        symbol = "✅" if passed else "❌"

        print(f"{symbol} {case['id']}: expected={expected_route} actual={actual_route}")

    total = len(dataset)
    accuracy = correct / total if total else 0

    print()
    print(f"Correct: {correct}/{total}")
    print(f"Router Accuracy: {accuracy:.2%}")

    failures = [result for result in results if not result["passed"]]

    if failures:
        print("\nFailures:")

        for failure in failures:
            print(
                f"- {failure['id']}: "
                f"{failure['expected_route']} -> "
                f"{failure['actual_route']}"
            )


if __name__ == "__main__":
    asyncio.run(evaluate_router())
