"""Unit-Tests für UniverseService mit gemocktem Repository."""

import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from backend.application.services.universe_service import UniverseService
from backend.domain.entities.universe import Universe

pytestmark = pytest.mark.unit


def _make_universe(name: str = "Test", tickers: tuple[str, ...] = ("AAPL", "MSFT")) -> Universe:
    return Universe(id=uuid.uuid4(), name=name, tickers=tickers, region="US")


def _make_service(universes: list[Universe] | None = None) -> tuple[UniverseService, MagicMock]:
    mock_repo = MagicMock()
    mock_repo.list = AsyncMock(return_value=universes or [])
    mock_repo.save = AsyncMock(return_value=None)
    service = UniverseService(universe_repo=mock_repo)
    return service, mock_repo


class TestListUniverses:
    async def test_list_returns_empty_when_no_universes(self) -> None:
        service, _ = _make_service([])
        result = await service.list()
        assert result == []

    async def test_list_returns_all_from_repo(self) -> None:
        expected = [_make_universe("Alpha"), _make_universe("Beta")]
        service, mock_repo = _make_service(expected)
        result = await service.list()
        mock_repo.list.assert_called_once()
        assert result == expected


class TestCreateUniverse:
    async def test_create_saves_and_returns_universe(self) -> None:
        service, mock_repo = _make_service()
        result = await service.create(name="My Universe", tickers=["AAPL", "MSFT"], region="US")
        assert result.name == "My Universe"
        assert result.region == "US"
        assert set(result.tickers) == {"AAPL", "MSFT"}
        mock_repo.save.assert_called_once_with(result)

    async def test_create_uppercase_tickers(self) -> None:
        service, mock_repo = _make_service()
        result = await service.create(name="Test", tickers=["aapl", "msft"], region="US")
        assert result.tickers == ("AAPL", "MSFT")

    async def test_create_generates_unique_ids(self) -> None:
        service, _ = _make_service()
        a = await service.create(name="A", tickers=["AAPL"], region="US")
        b = await service.create(name="B", tickers=["MSFT"], region="US")
        assert a.id != b.id
