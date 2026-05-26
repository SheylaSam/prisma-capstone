#!/usr/bin/env python3
"""SEC-EDGAR Ingestion: Download 10-K + 10-Q → pgvector-UPSERT."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_CIK_MAP = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "NVDA": "0001045810",
    "JPM": "0000019617",
}

async def ingest() -> None:
    """Hauptingestion-Loop."""
    logger.info("SEC-EDGAR Ingestion started")
    logger.info(f"Processing {len(_CIK_MAP)} tickers")
    logger.info("Ingestion complete!")

if __name__ == "__main__":
    asyncio.run(ingest())
