"""Integrationstests für /api/v1/universes Endpoints."""

import uuid
from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.domain.entities.universe import Universe
from backend.domain.repositories.universe_repository import UniverseRepository
from backend.interfaces.rest.app import create_app
from backend.interfaces.rest.dependencies import get_universe_repository

pytestmark = pytest.mark.integration

_SMI_ID = uuid.uuid4()
_SMI = Universe(
    id=_SMI_ID,
    name="SMI",
    region="CH",
    tickers=("NESN", "NOVN", "ROG"),
)


class _FakeUniverseRepo(UniverseRepository):
    def __init__(self, universes: list[Universe] | None = None) -> None:
        self._data: dict[UUID, Universe] = {u.id: u for u in (universes or [])}

    async def get(self, universe_id: UUID) -> Universe | None:
        return self._data.get(universe_id)

    async def list(self) -> list[Universe]:
        return sorted(self._data.values(), key=lambda u: u.name)

    async def save(self, universe: Universe) -> None:
        self._data[universe.id] = universe


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Client mit einem vorgeladenen Universe (SMI)."""
    app = create_app()
    repo = _FakeUniverseRepo([_SMI])
    app.dependency_overrides[get_universe_repository] = lambda: repo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


@pytest_asyncio.fixture
async def empty_client() -> AsyncGenerator[AsyncClient, None]:
    """Client ohne vorgeladene Universen."""
    app = create_app()
    repo = _FakeUniverseRepo()
    app.dependency_overrides[get_universe_repository] = lambda: repo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/v1/universes
# ---------------------------------------------------------------------------


async def test_list_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/universes")
    assert response.status_code == 200


async def test_list_returns_items_and_total(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/universes")).json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 1
    assert body["items"][0]["name"] == "SMI"


async def test_list_empty_returns_zero_total(empty_client: AsyncClient) -> None:
    body = (await empty_client.get("/api/v1/universes")).json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# POST /api/v1/universes
# ---------------------------------------------------------------------------


async def test_create_returns_201(empty_client: AsyncClient) -> None:
    response = await empty_client.post(
        "/api/v1/universes",
        json={"name": "DAX", "region": "DE", "tickers": ["SAP", "BMW"]},
    )
    assert response.status_code == 201


async def test_create_response_shape(empty_client: AsyncClient) -> None:
    body = (
        await empty_client.post(
            "/api/v1/universes",
            json={"name": "DAX", "region": "DE", "tickers": ["SAP", "BMW"]},
        )
    ).json()
    assert body["name"] == "DAX"
    assert body["region"] == "DE"
    assert set(body["tickers"]) == {"SAP", "BMW"}
    assert "id" in body


async def test_create_tickers_uppercased(empty_client: AsyncClient) -> None:
    body = (
        await empty_client.post(
            "/api/v1/universes",
            json={"name": "Test", "region": "US", "tickers": ["aapl", "msft"]},
        )
    ).json()
    assert "AAPL" in body["tickers"]
    assert "MSFT" in body["tickers"]


async def test_create_persists_and_is_listable(empty_client: AsyncClient) -> None:
    await empty_client.post(
        "/api/v1/universes",
        json={"name": "SP500", "region": "US", "tickers": ["AAPL"]},
    )
    body = (await empty_client.get("/api/v1/universes")).json()
    assert body["total"] == 1


async def test_create_empty_tickers_returns_422(empty_client: AsyncClient) -> None:
    response = await empty_client.post(
        "/api/v1/universes",
        json={"name": "Bad", "region": "US", "tickers": []},
    )
    assert response.status_code == 422


async def test_create_empty_name_returns_422(empty_client: AsyncClient) -> None:
    response = await empty_client.post(
        "/api/v1/universes",
        json={"name": "  ", "region": "US", "tickers": ["AAPL"]},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/universes/{id}
# ---------------------------------------------------------------------------


async def test_get_known_universe_returns_200(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/universes/{_SMI_ID}")
    assert response.status_code == 200


async def test_get_unknown_universe_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/universes/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_get_returns_correct_fields(client: AsyncClient) -> None:
    body = (await client.get(f"/api/v1/universes/{_SMI_ID}")).json()
    assert body["id"] == str(_SMI_ID)
    assert body["name"] == "SMI"
    assert body["region"] == "CH"
    assert set(body["tickers"]) == {"NESN", "NOVN", "ROG"}


# ---------------------------------------------------------------------------
# POST /api/v1/universes/{id}/sync
# ---------------------------------------------------------------------------


async def test_sync_known_universe_returns_200(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/universes/{_SMI_ID}/sync")
    assert response.status_code == 200


async def test_sync_unknown_universe_returns_404(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/universes/{uuid.uuid4()}/sync")
    assert response.status_code == 404


async def test_sync_response_shape(client: AsyncClient) -> None:
    body = (await client.post(f"/api/v1/universes/{_SMI_ID}/sync")).json()
    assert body["universe_id"] == str(_SMI_ID)
    assert "synced" in body
