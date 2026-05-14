"""MCP-Tool-Handler für `run_ranking`."""

from uuid import UUID

from backend.interfaces.mcp.rest_client import RESTClient

_WEIGHT_TOLERANCE = 1e-6


async def run_ranking(
    client: RESTClient,
    *,
    universe_id: str,
    weights: dict[str, float] | None = None,
) -> dict:  # type: ignore[type-arg]
    """Löst einen neuen Ranking-Run aus und gibt Top-10 zurück.

    Args:
        universe_id: UUID des Universums als String.
        weights: Optionale Modell-Gewichte (müssen auf 1.0 summieren).

    Returns:
        {"model_run_id": str, "n_stocks": int,
         "top_10_summary": [{"ticker": str, "total_rank": int|None, "sweet_spot": bool}]}
    """
    # Validierung: weights müssen auf 1.0 summieren
    if weights is not None:
        total = sum(weights.values())
        if abs(total - 1.0) > _WEIGHT_TOLERANCE:
            raise ValueError(f"Gewichte müssen 1.0 ergeben, nicht {total:.6f}")

    # Validierung: universe_id muss ein gültiges UUID-Format haben
    UUID(universe_id)

    payload: dict = {"universe_id": universe_id}  # type: ignore[type-arg]
    if weights is not None:
        payload["weight_config"] = weights

    run = await client.post("/api/v1/runs", json=payload)
    run_id = run["id"]

    rankings = await client.get(f"/api/v1/runs/{run_id}/rankings")

    sorted_rankings = sorted(
        rankings,
        key=lambda r: (r["total_rank"] is None, r["total_rank"] or 0),
    )
    top_10 = [
        {
            "ticker": r["ticker"],
            "total_rank": r["total_rank"],
            "sweet_spot": r["is_sweet_spot"],
        }
        for r in sorted_rankings[:10]
    ]

    return {
        "model_run_id": run_id,
        "n_stocks": len(rankings),
        "top_10_summary": top_10,
    }
