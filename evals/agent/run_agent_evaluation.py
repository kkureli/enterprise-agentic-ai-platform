import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid4

from app.agents.graph import agent_graph
from app.db.session import SessionLocal
from app.models import Asset
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from sqlalchemy import select

DATASET_PATH = Path(__file__).with_name("golden_dataset.json")

RESULTS_PATH = Path(__file__).resolve().parents[1] / "results" / "agent_evaluation.json"


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(
        encoding="utf-8",
    ) as file:
        return json.load(file)


async def get_tenant_id() -> UUID:
    async with SessionLocal() as session:
        tenant_id = await session.scalar(select(Asset.tenant_id).limit(1))

    if tenant_id is None:
        raise RuntimeError("No operational tenant found.")

    return tenant_id


async def evaluate_agent() -> None:
    dataset = load_dataset()
    tenant_id = await get_tenant_id()

    evaluation_results = []

    execution_success = 0
    route_correct = 0
    approval_correct = 0
    fully_passed = 0

    for case in dataset:
        thread_id = str(uuid4())

        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            "callbacks": [
                CallbackHandler(),
            ],
            "run_name": "agent-evaluation",
            "metadata": {
                "eval_case_id": case["id"],
                "tenant_id": str(tenant_id),
                "thread_id": thread_id,
            },
        }

        try:
            result = await agent_graph.ainvoke(
                {
                    "tenant_id": tenant_id,
                    "query": case["question"],
                    "retrieval_mode": "standard",
                },
                config=config,
            )

            execution_success += 1

            actual_route = result["route"]

            actual_approval = bool(result.get("__interrupt__"))

            route_passed = actual_route == case["expected_route"]

            approval_passed = actual_approval == case["expected_approval"]

            answer = result.get("final_answer") or result.get("tool_answer") or ""

            answer_present = bool(answer.strip())

            passed = route_passed and approval_passed and answer_present

            route_correct += int(route_passed)

            approval_correct += int(approval_passed)

            fully_passed += int(passed)

            evaluation_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected_route": (case["expected_route"]),
                    "actual_route": actual_route,
                    "expected_approval": (case["expected_approval"]),
                    "actual_approval": (actual_approval),
                    "answer": answer,
                    "route_passed": route_passed,
                    "approval_passed": (approval_passed),
                    "answer_present": (answer_present),
                    "passed": passed,
                    "error": None,
                }
            )

            symbol = "✅" if passed else "❌"

            print(
                f"{symbol} {case['id']}: "
                f"route={actual_route}, "
                f"approval={actual_approval}"
            )

            if not passed:
                print(
                    "   expected "
                    f"route={case['expected_route']}, "
                    "approval="
                    f"{case['expected_approval']}"
                )

        except Exception as exc:  # noqa: BLE001
            evaluation_results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected_route": (case["expected_route"]),
                    "actual_route": None,
                    "expected_approval": (case["expected_approval"]),
                    "actual_approval": None,
                    "answer": None,
                    "route_passed": False,
                    "approval_passed": False,
                    "answer_present": False,
                    "passed": False,
                    "error": (f"{type(exc).__name__}: {exc}"),
                }
            )

            print(f"💥 {case['id']}: {type(exc).__name__}: {exc}")

    total = len(dataset)

    route_accuracy = route_correct / total if total else 0

    approval_accuracy = approval_correct / total if total else 0

    execution_success_rate = execution_success / total if total else 0

    end_to_end_pass_rate = fully_passed / total if total else 0

    print()

    print(f"Route Accuracy: {route_correct}/{total} ({route_accuracy:.2%})")

    print(f"Approval Accuracy: {approval_correct}/{total} ({approval_accuracy:.2%})")

    print(
        "Execution Success Rate: "
        f"{execution_success}/{total} "
        f"({execution_success_rate:.2%})"
    )

    print(f"End-to-End Pass Rate: {fully_passed}/{total} ({end_to_end_pass_rate:.2%})")

    output = {
        "total_cases": total,
        "metrics": {
            "route_accuracy": (route_accuracy),
            "approval_accuracy": (approval_accuracy),
            "execution_success_rate": (execution_success_rate),
            "end_to_end_pass_rate": (end_to_end_pass_rate),
        },
        "results": evaluation_results,
    }

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nResults saved to: {RESULTS_PATH}")

    get_client().flush()


if __name__ == "__main__":
    asyncio.run(evaluate_agent())
