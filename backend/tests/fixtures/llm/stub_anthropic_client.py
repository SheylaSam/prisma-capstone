"""Stub fuer den Anthropic-SDK-Client in Integration-Tests."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


class StubMessages:
    def __init__(self, fixtures: list[Path]) -> None:
        self._fixtures = list(fixtures)
        self._idx = 0
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._idx >= len(self._fixtures):
            raise RuntimeError("StubMessages: kein Fixture mehr verfuegbar")
        path = self._fixtures[self._idx]
        self._idx += 1
        data = json.loads(path.read_text(encoding="utf-8"))
        return _to_namespace(data)


class StubAnthropicClient:
    def __init__(self, fixture_paths: list[Path]) -> None:
        self.messages = StubMessages(fixture_paths)


def _to_namespace(obj: Any, *, _key: str | None = None) -> Any:
    """Dict → SimpleNamespace rekursiv.

    Ausnahme: Der Wert unter dem Schluessel ``input`` bleibt ein plain dict,
    damit `ResearchMemoSchema.model_validate(block.input)` wie gegen das echte
    Anthropic SDK funktioniert (das ebenfalls `input` als dict zurueckgibt).
    """
    if isinstance(obj, dict):
        if _key == "input":
            # Tool-use input bleibt dict — Pydantic model_validate erwartet dict
            return obj
        return SimpleNamespace(**{k: _to_namespace(v, _key=k) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_namespace(x, _key=_key) for x in obj]
    return obj
