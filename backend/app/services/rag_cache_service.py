import hashlib
import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING
from uuid import UUID

from app.core.config import settings
from app.services.redis_service import get_redis
from app.services.retrieval_service import RetrievalFilters

if TYPE_CHECKING:
    from app.services.rag_service import RagResult

logger = logging.getLogger(__name__)


def normalize_question(question: str) -> str:
    return " ".join(question.lower().split())


def _question_identity_hash(
    question: str,
    *,
    limit: int,
    filters: RetrievalFilters | None,
) -> str:
    filter_document_id = ""
    filter_filename = ""

    if filters is not None:
        if filters.document_id is not None:
            filter_document_id = str(filters.document_id)
        if filters.filename is not None:
            filter_filename = filters.filename.strip().lower()

    material = "|".join(
        [
            normalize_question(question),
            str(limit),
            filter_document_id,
            filter_filename,
        ]
    )

    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _version_key(tenant_id: UUID) -> str:
    return f"rag_version:{tenant_id}"


def _cache_key(
    tenant_id: UUID,
    *,
    version: int,
    retrieval_mode: str,
    question_hash: str,
) -> str:
    return f"rag:{tenant_id}:{version}:{retrieval_mode}:{question_hash}"


def build_rag_cache_key(
    tenant_id: UUID,
    question: str,
    *,
    version: int,
    retrieval_mode: str,
    limit: int,
    filters: RetrievalFilters | None = None,
) -> str:
    question_hash = _question_identity_hash(
        question,
        limit=limit,
        filters=filters,
    )
    return _cache_key(
        tenant_id,
        version=version,
        retrieval_mode=retrieval_mode,
        question_hash=question_hash,
    )


def _serialize_rag_result(result: "RagResult") -> str:
    return json.dumps(
        {
            "answer": result.answer,
            "sources": [asdict(source) for source in result.sources],
            "retrieved_chunks": [asdict(chunk) for chunk in result.retrieved_chunks],
        }
    )


def _deserialize_rag_result(payload: str) -> "RagResult":
    from app.services.rag_service import RagResult, RagRetrievedChunk, RagSource

    data = json.loads(payload)

    return RagResult(
        answer=data["answer"],
        sources=[
            RagSource(
                **{
                    key: value
                    for key, value in source.items()
                    if key in RagSource.__dataclass_fields__
                }
            )
            for source in data.get("sources", [])
        ],
        retrieved_chunks=[
            RagRetrievedChunk(
                **{
                    key: value
                    for key, value in chunk.items()
                    if key in RagRetrievedChunk.__dataclass_fields__
                }
            )
            for chunk in data.get("retrieved_chunks", [])
        ],
        cache_hit=False,
    )


async def get_rag_cache_version(tenant_id: UUID) -> int:
    redis = get_redis()

    if redis is None:
        return 0

    try:
        value = await redis.get(_version_key(tenant_id))
    except Exception:
        logger.warning(
            "Redis cache failure reading rag version tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        return 0

    if value is None:
        return 0

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def increment_rag_cache_version(tenant_id: UUID) -> None:
    redis = get_redis()

    if redis is None:
        return

    try:
        await redis.incr(_version_key(tenant_id))
        logger.info(
            "RAG cache version incremented tenant_id=%s",
            tenant_id,
        )
    except Exception:
        logger.warning(
            "Redis cache failure incrementing rag version tenant_id=%s",
            tenant_id,
            exc_info=True,
        )


async def get_cached_rag_result(
    tenant_id: UUID,
    question: str,
    *,
    limit: int,
    retrieval_mode: str,
    filters: RetrievalFilters | None = None,
) -> "RagResult | None":
    redis = get_redis()

    if redis is None:
        return None

    try:
        version = await get_rag_cache_version(tenant_id)
        key = build_rag_cache_key(
            tenant_id,
            question,
            version=version,
            retrieval_mode=retrieval_mode,
            limit=limit,
            filters=filters,
        )
        payload = await redis.get(key)
    except Exception:
        logger.warning(
            "Redis cache failure on get tenant_id=%s retrieval_mode=%s",
            tenant_id,
            retrieval_mode,
            exc_info=True,
        )
        return None

    if payload is None:
        logger.info(
            "RAG cache miss tenant_id=%s retrieval_mode=%s",
            tenant_id,
            retrieval_mode,
        )
        return None

    try:
        result = _deserialize_rag_result(payload)
    except Exception:
        logger.warning(
            "Redis cache failure deserializing payload tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        return None

    logger.info(
        "RAG cache hit tenant_id=%s retrieval_mode=%s",
        tenant_id,
        retrieval_mode,
    )
    return result


async def set_cached_rag_result(
    tenant_id: UUID,
    question: str,
    result: "RagResult",
    *,
    limit: int,
    retrieval_mode: str,
    filters: RetrievalFilters | None = None,
) -> None:
    redis = get_redis()

    if redis is None:
        return

    try:
        version = await get_rag_cache_version(tenant_id)
        key = build_rag_cache_key(
            tenant_id,
            question,
            version=version,
            retrieval_mode=retrieval_mode,
            limit=limit,
            filters=filters,
        )
        await redis.set(
            key,
            _serialize_rag_result(result),
            ex=settings.rag_cache_ttl_seconds,
        )
    except Exception:
        logger.warning(
            "Redis cache failure on set tenant_id=%s retrieval_mode=%s",
            tenant_id,
            retrieval_mode,
            exc_info=True,
        )
