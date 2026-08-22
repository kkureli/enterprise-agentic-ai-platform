# Recall@K
# → doğru dokümanların kaç tanesini ilk K'da bulduk?

# MRR
# → ilk doğru doküman kaçıncı sırada?

# nDCG@K
# → doğru dokümanlar ne kadar yukarı sırada?
import math


def deduplicate_ranked_documents(
    retrieved_documents: list[str],
) -> list[str]:
    seen: set[str] = set()
    unique_documents: list[str] = []

    for document in retrieved_documents:
        if document in seen:
            continue

        seen.add(document)
        unique_documents.append(document)

    return unique_documents


def recall_at_k(
    retrieved_documents: list[str],
    relevant_documents: list[str],
    k: int,
) -> float:
    if not relevant_documents:
        return 0.0

    retrieved = deduplicate_ranked_documents(
        retrieved_documents,
    )[:k]

    relevant = set(relevant_documents)

    hits = sum(1 for document in retrieved if document in relevant)

    return hits / len(relevant)


def reciprocal_rank(
    retrieved_documents: list[str],
    relevant_documents: list[str],
) -> float:
    relevant = set(relevant_documents)

    for rank, document in enumerate(
        deduplicate_ranked_documents(retrieved_documents),
        start=1,
    ):
        if document in relevant:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    retrieved_documents: list[str],
    relevant_documents: list[str],
    k: int,
) -> float:
    if not relevant_documents:
        return 0.0

    relevant = set(relevant_documents)

    retrieved = deduplicate_ranked_documents(
        retrieved_documents,
    )[:k]

    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, document in enumerate(retrieved, start=1)
        if document in relevant
    )

    ideal_hits = min(
        len(relevant),
        k,
    )

    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))

    if idcg == 0.0:
        return 0.0

    return dcg / idcg
