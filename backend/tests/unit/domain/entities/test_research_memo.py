"""Unit-Tests für ContradictionItem Value-Object (ResearchMemo)."""

import pytest
from pydantic import ValidationError

from backend.domain.entities.research_memo import ContradictionItem

pytestmark = pytest.mark.unit


class TestContradictionItem:
    def test_valid_construct(self) -> None:
        item = ContradictionItem(
            model_a="Quality Classic",
            model_b="Diversification",
            description="Top in Quality, schwach in Risiko-Diversifikation.",
        )
        assert item.model_a == "Quality Classic"

    def test_is_frozen(self) -> None:
        item = ContradictionItem(model_a="A", model_b="B", description="x" * 50)
        with pytest.raises(ValidationError):
            item.model_a = "C"

    def test_description_max_length_200(self) -> None:
        with pytest.raises(ValidationError):
            ContradictionItem(model_a="A", model_b="B", description="x" * 201)

    def test_model_a_min_length_1(self) -> None:
        with pytest.raises(ValidationError):
            ContradictionItem(model_a="", model_b="B", description="x" * 50)

    def test_model_a_max_length_64(self) -> None:
        with pytest.raises(ValidationError):
            ContradictionItem(model_a="x" * 65, model_b="B", description="x" * 50)
