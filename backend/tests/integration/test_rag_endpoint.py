"""Integration-Tests für RAG-Endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rag_retrieve_query_validation(http_client: AsyncClient) -> None:
    """Query < 1 Zeichen wird abgelehnt."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "", "k": 5})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_rag_retrieve_query_max(http_client: AsyncClient) -> None:
    """Query > 2000 Zeichen wird abgelehnt."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "x" * 2001, "k": 5})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_rag_retrieve_k_min(http_client: AsyncClient) -> None:
    """k < 1 wird abgelehnt."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "test", "k": 0})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_rag_retrieve_k_max(http_client: AsyncClient) -> None:
    """k > 20 wird abgelehnt."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "test", "k": 21})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_rag_retrieve_ticker_invalid(http_client: AsyncClient) -> None:
    """Ungültiges Ticker-Format wird abgelehnt."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "test", "k": 5, "ticker": "INVALID123"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_rag_retrieve_default_k(http_client: AsyncClient) -> None:
    """Default k=5 wird verwendet."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "test query"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rag_retrieve_response(http_client: AsyncClient) -> None:
    """Response hat korrekte Struktur."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "test", "k": 5})
    assert response.status_code == 200
    data = response.json()
    assert "total" in data and "results" in data

@pytest.mark.asyncio
async def test_rag_retrieve_no_results(http_client: AsyncClient) -> None:
    """Bei leerer DB ist total=0."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "nonexistent", "k": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_rag_retrieve_ticker_filter(http_client: AsyncClient) -> None:
    """Ticker-Filter wird akzeptiert."""
    response = await http_client.post("/api/v1/rag/retrieve", json={"query": "test", "k": 5, "ticker": "AAPL"})
    assert response.status_code == 200
