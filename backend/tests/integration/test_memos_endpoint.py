"""Integration-Tests fuer /api/v1/memos/* via FastAPI-TestClient."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from backend.application.services.narrative_service import NarrativeService
from backend.domain.entities.research_memo import ResearchMemo
from backend.interfaces.rest.app import create_app
from backend.interfaces.rest.dependencies import get_narrative_service

pytestmark = pytest.mark.integration


def _sample_memo() -> ResearchMemo:
    return ResearchMemo(
        id=uuid4(),
        stock_id=uuid4(),
        model_run_id=uuid4(),
        language="de",
        created_at=datetime.now(tz=UTC),
        one_liner="One-Liner.",
        ranking_interpretation="x" * 120,
        sweet_spot=True,
        sweet_spot_explanation="Top 25% in 4 Modellen.",
        contradictions=[],
        key_strengths=["Top 10% Quality"],
        key_risks=["Bewertungs-Multiples"],
        confidence="high",
        model_version="claude-sonnet-4-6",
    )


@pytest_asyncio.fixture
async def app_with_mock_service() -> Any:
    app = create_app()
    mock_service = AsyncMock(spec=NarrativeService)
    app.dependency_overrides[get_narrative_service] = lambda: mock_service
    yield app, mock_service
    app.dependency_overrides.clear()


def test_post_generate_returns_200_with_memo(
    app_with_mock_service: tuple[Any, AsyncMock],
) -> None:
    app, mock_service = app_with_mock_service
    memo = _sample_memo()
    mock_service.generate_memo = AsyncMock(return_value=memo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/memos/generate",
            json={
                "stock_id": str(memo.stock_id),
                "model_run_id": str(memo.model_run_id),
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["one_liner"] == "One-Liner."
    assert body["is_error"] is False


def test_post_generate_returns_404_when_stock_missing(
    app_with_mock_service: tuple[Any, AsyncMock],
) -> None:
    app, mock_service = app_with_mock_service
    mock_service.generate_memo = AsyncMock(side_effect=LookupError("Stock not found"))

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/memos/generate",
            json={"stock_id": str(uuid4()), "model_run_id": str(uuid4())},
        )

    assert resp.status_code == 404


def test_get_memo_returns_200_when_exists(
    app_with_mock_service: tuple[Any, AsyncMock],
) -> None:
    app, mock_service = app_with_mock_service
    memo = _sample_memo()
    mock_service.get_memo = AsyncMock(return_value=memo)

    with TestClient(app) as client:
        resp = client.get(f"/api/v1/memos/{memo.stock_id}/{memo.model_run_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["confidence"] == "high"


def test_get_memo_returns_404_when_missing(
    app_with_mock_service: tuple[Any, AsyncMock],
) -> None:
    app, mock_service = app_with_mock_service
    mock_service.get_memo = AsyncMock(return_value=None)

    with TestClient(app) as client:
        resp = client.get(f"/api/v1/memos/{uuid4()}/{uuid4()}")

    assert resp.status_code == 404


def test_post_generate_sets_is_error_when_fallback_memo(
    app_with_mock_service: tuple[Any, AsyncMock],
) -> None:
    app, mock_service = app_with_mock_service
    memo = _sample_memo().model_copy(
        update={
            "model_version": "error-fallback",
            "one_liner": "Memo-Generierung fehlgeschlagen — bitte Run regenerieren",
            "confidence": "low",
        }
    )
    mock_service.generate_memo = AsyncMock(return_value=memo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/memos/generate",
            json={"stock_id": str(memo.stock_id), "model_run_id": str(memo.model_run_id)},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_error"] is True
