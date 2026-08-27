from uuid import uuid4

import pytest

from app.services.rag_service import (
    RagResult,
    RagRetrievedChunk,
    RagSource,
)
from app.services.retrieval_service import retrieve_chunks


@pytest.mark.asyncio
async def test_retrieval_is_tenant_scoped(monkeypatch):
    tenant_id = uuid4()

    class FakeResult:
        points = []

    class FakeQdrantClient:
        query_filter = None

        async def query_points(
            self,
            *,
            collection_name,
            query,
            using,
            query_filter,
            limit,
            with_payload,
        ):
            self.query_filter = query_filter
            self.using = using

            return FakeResult()

        async def close(self):
            pass

    fake_client = FakeQdrantClient()

    async def fake_embed_query(query):
        return [0.1, 0.2, 0.3]

    def fake_get_qdrant_client():
        return fake_client

    monkeypatch.setattr(
        "app.services.retrieval_service.embed_query",
        fake_embed_query,
    )

    monkeypatch.setattr(
        "app.services.retrieval_service.get_qdrant_client",
        fake_get_qdrant_client,
    )

    await retrieve_chunks(
        tenant_id=tenant_id,
        query="test query",
        limit=5,
    )

    filter_data = fake_client.query_filter.model_dump()

    assert filter_data["must"][0]["key"] == "tenant_id"
    assert filter_data["must"][0]["match"]["value"] == str(tenant_id)


@pytest.mark.asyncio
async def test_empty_document_is_rejected(client):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "Document Test Tenant"},
    )

    tenant_id = tenant_response.json()["id"]

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/documents",
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == ("Document contains no extractable text.")


@pytest.mark.asyncio
async def test_rag_response_contains_sources_and_retrieved_chunks(
    client,
    monkeypatch,
):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "RAG Test Tenant"},
    )

    tenant_id = tenant_response.json()["id"]

    async def fake_answer_question(
        tenant_id,
        question,
        limit,
        filters=None,
        retrieval_mode="standard",
        response_language=None,
    ):
        return RagResult(
            answer="Employees receive 20 working days of paid annual leave.",
            sources=[
                RagSource(
                    document_id="document-1",
                    filename="vacation-policy.txt",
                    chunk_index=0,
                    score=0.75,
                )
            ],
            retrieved_chunks=[
                RagRetrievedChunk(
                    document_id="document-1",
                    filename="vacation-policy.txt",
                    chunk_index=0,
                    score=0.75,
                    text="Employees receive 20 working days of paid leave.",
                ),
                RagRetrievedChunk(
                    document_id="document-2",
                    filename="network-security.txt",
                    chunk_index=0,
                    score=0.15,
                    text="Remote access requires VPN and MFA.",
                ),
            ],
        )

    monkeypatch.setattr(
        "app.api.v1.rag.answer_question",
        fake_answer_question,
    )

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/rag",
        json={
            "question": "How much annual leave do employees receive?",
            "limit": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == ("Employees receive 20 working days of paid annual leave.")

    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "vacation-policy.txt"

    assert len(data["retrieved_chunks"]) == 2


@pytest.mark.asyncio
async def test_invalid_retrieval_mode_returns_422(client):
    tenant_response = await client.post(
        "/api/v1/tenants",
        json={"name": "RAG Mode Test Tenant"},
    )

    tenant_id = tenant_response.json()["id"]

    response = await client.post(
        f"/api/v1/tenants/{tenant_id}/rag",
        json={
            "question": "How much annual leave do employees receive?",
            "limit": 3,
            "retrieval_mode": "experimental",
        },
    )

    assert response.status_code == 422
