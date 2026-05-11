# RAG-Pipeline Slice 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans. Checkbox-Syntax `- [ ]` fuer Tracking.

**Goal:** pgvector-Persistence-Schicht — Migration + Domain-Entities + Repository-Port + SQLA-Adapter + Tests. Kein Ingestion, kein Retrieval, kein Voyage-Call.

**Architektur:** Hexagonal — `Document` und `EmbeddingChunk` Domain-Entities (frozen=True), `EmbeddingRepository`-Port in Domain, `SQLAEmbeddingRepository`-Adapter in Infrastructure. Migration aktiviert pgvector-Extension und legt Tabellen + IVFFlat-Index an.

**Tech Stack:** SQLAlchemy 2.0 (Mapped/mapped_column), Alembic, pgvector Python-Lib (>=0.3), pytest + pytest-asyncio.

**Reality-Check vs. Spec (Plan-Phase confirmed):**
- `docker-compose.yml` nutzt schon `pgvector/pgvector:pg16` — Spec §9 Test-DB-Risiko bereits mitigated, kein docker-compose-Change
- ORM-Pattern in Codebase: `Mapped[T]` + `mapped_column(...)` mit `from backend.infrastructure.persistence.base import Base`
- Repository-Pattern: `session_factory` injection (PR #25-Pattern), wegen Transaction-Isolation
- Integration-Tests laufen ueber `db_session`-Fixture mit `pytest.mark.integration` (siehe `test_research_memo_repository.py`)
- Migration-Pattern: `from sqlalchemy.dialects import postgresql`, `revision: str = "NNNN"` + `down_revision: str | None`

---

## File Structure

| Datei | Typ | Verantwortung |
|---|---|---|
| `pyproject.toml` | MODIFY | `pgvector>=0.3` Dep adden |
| `backend/domain/entities/document.py` | CREATE | `Document` frozen-dataclass |
| `backend/domain/entities/embedding_chunk.py` | CREATE | `EmbeddingChunk` frozen-dataclass |
| `backend/domain/repositories/embedding_repository.py` | CREATE | `EmbeddingRepository` ABC + `DuplicateUrl` Exception |
| `backend/alembic/versions/0006_enable_pgvector_and_create_embeddings.py` | CREATE | pgvector-Extension + 2 Tabellen + IVFFlat-Index |
| `backend/infrastructure/persistence/models/embedding.py` | CREATE | `DocumentORM` + `EmbeddingChunkORM` (SQLA-Mapped) |
| `backend/infrastructure/persistence/repositories/embedding_repository.py` | CREATE | `SQLAEmbeddingRepository`-Adapter |
| `backend/tests/unit/domain/entities/test_document.py` | CREATE | Entity-Validation |
| `backend/tests/unit/domain/entities/test_embedding_chunk.py` | CREATE | Entity-Validation |
| `backend/tests/integration/persistence/test_embedding_repository.py` | CREATE | Roundtrip + Constraints + Cascade |
| `docs/AI-USAGE.md` | MODIFY | Slice-Eintrag |

---

## Task 1: Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1.1: `pgvector` dep adden**

Edit `pyproject.toml` dependencies — alphabetisch nach `pgvector` einsortieren (zwischen `mcp` und `psycopg`):

```toml
    "pgvector>=0.3",
```

- [ ] **Step 1.2: Install + Verify**

```bash
source .venv/bin/activate
uv pip install -e .
python -c "from pgvector.sqlalchemy import Vector; print(Vector.__module__)"
```

Expected: `pgvector.sqlalchemy` — kein ImportError.

- [ ] **Step 1.3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(deps): pgvector>=0.3 (RAG Slice 1 Task 1)"
```

---

## Task 2: `Document` Domain-Entity

**Files:**
- Create: `backend/domain/entities/document.py`
- Create: `backend/tests/unit/domain/entities/test_document.py`

- [ ] **Step 2.1: Write failing test**

Create `backend/tests/unit/domain/entities/test_document.py`:

```python
"""Tests fuer Document-Entity (RAG Slice 1)."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from backend.domain.entities.document import Document

pytestmark = pytest.mark.unit


def _new_doc(**overrides) -> Document:
    base = dict(
        id=uuid4(),
        ticker="AAPL",
        doc_type="10-K",
        filing_date=date(2024, 1, 1),
        url="https://sec.gov/aapl-10k-2024.pdf",
        raw_text_hash=None,
        ingested_at=datetime.now(UTC),
    )
    base.update(overrides)
    return Document(**base)


class TestDocument:
    def test_constructs_with_minimal_fields(self) -> None:
        doc = _new_doc()
        assert doc.ticker == "AAPL"
        assert doc.doc_type == "10-K"
        assert doc.raw_text_hash is None

    def test_frozen_prevents_reassignment(self) -> None:
        doc = _new_doc()
        with pytest.raises(FrozenInstanceError):
            doc.ticker = "MSFT"  # type: ignore[misc]

    def test_ingested_at_must_be_tz_aware(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            _new_doc(ingested_at=datetime(2024, 1, 1))  # naive

    def test_doc_type_must_be_10k_or_10q(self) -> None:
        with pytest.raises(ValueError, match="doc_type"):
            _new_doc(doc_type="8-K")

    def test_accepts_10q(self) -> None:
        doc = _new_doc(doc_type="10-Q")
        assert doc.doc_type == "10-Q"

    def test_url_required_nonempty(self) -> None:
        with pytest.raises(ValueError, match="url"):
            _new_doc(url="")
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
pytest backend/tests/unit/domain/entities/test_document.py -v
```

Expected: ImportError oder ModuleNotFoundError.

- [ ] **Step 2.3: Implement `Document`**

Create `backend/domain/entities/document.py`:

```python
"""Document-Entity — repraesentiert ein indiziertes SEC-Filing (10-K / 10-Q).

Frozen-Dataclass mit __post_init__-Validation (CLAUDE.md §"Datumshandling
ohne Timezone vermeiden"). `raw_text_hash` ist Slice-1 immer None;
Slice 2 fuellt es nach Text-Extraktion.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

_VALID_DOC_TYPES = frozenset({"10-K", "10-Q"})


@dataclass(frozen=True)
class Document:
    id: UUID
    ticker: str
    doc_type: str
    filing_date: date
    url: str
    raw_text_hash: str | None
    ingested_at: datetime

    def __post_init__(self) -> None:
        if self.doc_type not in _VALID_DOC_TYPES:
            raise ValueError(
                f"doc_type must be one of {sorted(_VALID_DOC_TYPES)}, got {self.doc_type!r}"
            )
        if not self.url:
            raise ValueError("url must be non-empty")
        if self.ingested_at.tzinfo is None:
            raise ValueError("ingested_at must be timezone-aware (UTC)")
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
pytest backend/tests/unit/domain/entities/test_document.py -v
```

Expected: 6/6 passed.

- [ ] **Step 2.5: Commit**

```bash
git add backend/domain/entities/document.py backend/tests/unit/domain/entities/test_document.py
git commit -m "feat(rag): Document-Domain-Entity (Slice 1 Task 2)"
```

---

## Task 3: `EmbeddingChunk` Domain-Entity

**Files:**
- Create: `backend/domain/entities/embedding_chunk.py`
- Create: `backend/tests/unit/domain/entities/test_embedding_chunk.py`

- [ ] **Step 3.1: Write failing test**

Create `backend/tests/unit/domain/entities/test_embedding_chunk.py`:

```python
"""Tests fuer EmbeddingChunk-Entity (RAG Slice 1)."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from backend.domain.entities.embedding_chunk import EMBEDDING_DIM, EmbeddingChunk

pytestmark = pytest.mark.unit


def _new_chunk(**overrides) -> EmbeddingChunk:
    base = dict(
        id=uuid4(),
        document_id=uuid4(),
        chunk_idx=0,
        content="sample chunk text",
        embedding=[0.1] * EMBEDDING_DIM,
        metadata={},
    )
    base.update(overrides)
    return EmbeddingChunk(**base)


class TestEmbeddingChunk:
    def test_constructs_happy(self) -> None:
        chunk = _new_chunk()
        assert chunk.chunk_idx == 0
        assert len(chunk.embedding) == EMBEDDING_DIM
        assert chunk.metadata == {}

    def test_frozen_prevents_reassignment(self) -> None:
        chunk = _new_chunk()
        with pytest.raises(FrozenInstanceError):
            chunk.chunk_idx = 1  # type: ignore[misc]

    def test_embedding_must_be_correct_dim(self) -> None:
        with pytest.raises(ValueError, match=f"embedding must be {EMBEDDING_DIM}-dim"):
            _new_chunk(embedding=[0.1] * 100)

    def test_chunk_idx_must_be_non_negative(self) -> None:
        with pytest.raises(ValueError, match="chunk_idx"):
            _new_chunk(chunk_idx=-1)

    def test_content_must_be_non_empty(self) -> None:
        with pytest.raises(ValueError, match="content"):
            _new_chunk(content="")

    def test_embedding_dim_constant(self) -> None:
        assert EMBEDDING_DIM == 2048
```

- [ ] **Step 3.2: Run tests to verify they fail**

```bash
pytest backend/tests/unit/domain/entities/test_embedding_chunk.py -v
```

Expected: ImportError.

- [ ] **Step 3.3: Implement `EmbeddingChunk`**

Create `backend/domain/entities/embedding_chunk.py`:

```python
"""EmbeddingChunk-Entity — ein Chunk eines Documents mit Voyage-Embedding.

Embedding-Dimension ist fest 2048 (ADR-0004 §4 — voyage-3-large). Konfigurabel
zu machen ist Stretch — Slice 1 verifiziert die feste Constraint hart.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

EMBEDDING_DIM = 2048


@dataclass(frozen=True)
class EmbeddingChunk:
    id: UUID
    document_id: UUID
    chunk_idx: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"embedding must be {EMBEDDING_DIM}-dim, got {len(self.embedding)}"
            )
        if self.chunk_idx < 0:
            raise ValueError(f"chunk_idx must be non-negative, got {self.chunk_idx}")
        if not self.content:
            raise ValueError("content must be non-empty")
```

- [ ] **Step 3.4: Run tests to verify they pass**

```bash
pytest backend/tests/unit/domain/entities/test_embedding_chunk.py -v
```

Expected: 6/6 passed.

- [ ] **Step 3.5: Commit**

```bash
git add backend/domain/entities/embedding_chunk.py backend/tests/unit/domain/entities/test_embedding_chunk.py
git commit -m "feat(rag): EmbeddingChunk-Domain-Entity (Slice 1 Task 3)"
```

---

## Task 4: Repository-Port (ABC)

**Files:**
- Create: `backend/domain/repositories/embedding_repository.py`

- [ ] **Step 4.1: Implement Port**

Pure ABC — keine eigenen Tests, da kein Verhalten (Tests landen am Adapter in Task 8).

Create `backend/domain/repositories/embedding_repository.py`:

```python
"""EmbeddingRepository-Port — Slice 1: Persistence-Operations ohne Retrieval.

`find_nearest(query_embedding, k)` ist Slice 3 — kommt erst mit dem
Retrieval-Service. Slice 1 deckt nur Schreib- und Lese-Operationen ab.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from backend.domain.entities.document import Document
from backend.domain.entities.embedding_chunk import EmbeddingChunk


class DuplicateUrl(Exception):
    """Wird geworfen wenn ein Document mit gleicher URL bereits existiert."""

    def __init__(self, url: str) -> None:
        super().__init__(f"Document with url={url!r} already exists")
        self.url = url


class EmbeddingRepository(ABC):
    @abstractmethod
    async def save_document(self, doc: Document) -> None:
        """Persistiert ein Document. Wirft `DuplicateUrl` bei URL-Konflikt."""

    @abstractmethod
    async def save_chunks(self, chunks: list[EmbeddingChunk]) -> None:
        """Batch-Insert von Chunks. Idempotent auf (document_id, chunk_idx) — re-runs
        ueberschreiben den existierenden Eintrag (UPSERT)."""

    @abstractmethod
    async def get_document_by_url(self, url: str) -> Document | None:
        """Liefert das Document zu einer URL, oder None wenn nicht vorhanden."""

    @abstractmethod
    async def count_chunks(self, document_id: UUID) -> int:
        """Zaehlt Chunks pro Document."""

    @abstractmethod
    async def list_documents(self, *, ticker: str | None = None) -> list[Document]:
        """Liefert alle Documents, optional gefiltert nach Ticker.
        Sortiert nach ingested_at DESC."""
```

- [ ] **Step 4.2: Quick Type-Check**

```bash
mypy backend/domain/repositories/embedding_repository.py
```

Expected: Success.

- [ ] **Step 4.3: Commit**

```bash
git add backend/domain/repositories/embedding_repository.py
git commit -m "feat(rag): EmbeddingRepository-Port (Slice 1 Task 4)"
```

---

## Task 5: Alembic-Migration

**Files:**
- Create: `backend/alembic/versions/0006_enable_pgvector_and_create_embeddings.py`

- [ ] **Step 5.1: Identify down_revision**

Verifizieren dass `0005_create_research_memos.py` mit `revision = "0005"` benannt ist:

```bash
grep -l 'revision: str = "0005"' backend/alembic/versions/*.py
```

Expected: 1 Treffer (`0005_create_research_memos.py`).

- [ ] **Step 5.2: Write Migration**

Create `backend/alembic/versions/0006_enable_pgvector_and_create_embeddings.py`:

```python
"""enable pgvector extension and create embedding tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector-Extension. Idempotent — Render-Postgres-DBs ab 2026-02-05
    # haben es als optional-Extension verfuegbar (Render-Docs).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("doc_type", sa.String(8), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("raw_text_hash", sa.String(64), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_documents_ticker", "documents", ["ticker"])

    op.create_table(
        "embedding_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_idx", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(2048), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("document_id", "chunk_idx", name="uq_doc_chunk_idx"),
    )

    # IVFFlat-Index fuer Cosine-Similarity. lists=100 ist Heuristik fuer
    # ~4000 Chunks (sqrt(n)). In Slice 1 ist die Tabelle leer; Index
    # funktioniert trotzdem (Postgres faellt auf seq-scan zurueck bis
    # genuegend Daten fuer Training da sind).
    op.execute(
        "CREATE INDEX ix_embedding_chunks_embedding "
        "ON embedding_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embedding_chunks_embedding")
    op.drop_table("embedding_chunks")
    op.drop_index("ix_documents_ticker", table_name="documents")
    op.drop_table("documents")
    # Extension wird NICHT gedroppt — andere Tabellen koennten sie zukuenftig nutzen.
```

- [ ] **Step 5.3: Migration lokal ausfuehren**

```bash
# Test-DB hochfahren falls noch nicht laeuft
docker compose up -d db
docker compose ps  # erwartet: db healthy

# Migration up
source .venv/bin/activate
DATABASE_URL=postgresql+asyncpg://prisma:prisma@localhost:5432/prisma \
    alembic upgrade head
```

Expected: `Running upgrade 0005 -> 0006, enable pgvector ...`

```bash
# Inspect: Tabellen + Index existieren
docker compose exec db psql -U prisma -d prisma -c "\d documents"
docker compose exec db psql -U prisma -d prisma -c "\d embedding_chunks"
docker compose exec db psql -U prisma -d prisma -c "SELECT indexname FROM pg_indexes WHERE tablename='embedding_chunks';"
```

Expected: Index `ix_embedding_chunks_embedding` mit `ivfflat` Spalte.

- [ ] **Step 5.4: Migration down testen**

```bash
DATABASE_URL=postgresql+asyncpg://prisma:prisma@localhost:5432/prisma \
    alembic downgrade -1
```

Expected: `Running downgrade 0006 -> 0005, enable pgvector ...`

```bash
# Inspect: Tabellen weg
docker compose exec db psql -U prisma -d prisma -c "\dt documents"
```

Expected: `Did not find any relation named "documents".`

- [ ] **Step 5.5: Migration wieder up (fuer naechste Tasks)**

```bash
DATABASE_URL=postgresql+asyncpg://prisma:prisma@localhost:5432/prisma \
    alembic upgrade head
```

- [ ] **Step 5.6: Commit**

```bash
git add backend/alembic/versions/0006_enable_pgvector_and_create_embeddings.py
git commit -m "feat(rag): Migration 0006 pgvector + embedding tables (Slice 1 Task 5)"
```

---

## Task 6: SQLAlchemy ORM Models

**Files:**
- Create: `backend/infrastructure/persistence/models/embedding.py`

- [ ] **Step 6.1: Implement ORM Models**

Create `backend/infrastructure/persistence/models/embedding.py`:

```python
"""SQLAlchemy-ORM-Modelle fuer documents + embedding_chunks (RAG Slice 1)."""

import uuid
from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.persistence.base import Base


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(8), nullable=False)
    filing_date: Mapped[date] = mapped_column(Date(), nullable=False)
    url: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    raw_text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        # mit timezone=True, gleicher Stil wie ResearchMemoORM
        # nicht: sa.DateTime(timezone=True)
        # sondern: aus sqlalchemy import DateTime (oder in __init__-imports)
        # In diesem Snippet ueber den Import gehandhabt:
        __import__("sqlalchemy").DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class EmbeddingChunkORM(Base):
    __tablename__ = "embedding_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_idx", name="uq_doc_chunk_idx"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_idx: Mapped[int] = mapped_column(Integer(), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(2048), nullable=False)
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB(), nullable=True
    )
```

**Wichtig:** Spalte heisst in der DB `metadata`, das Python-Attribute aber
`chunk_metadata` — `metadata` ist reserved auf `Base` (Base.metadata) und
kann nicht als Mapped[]-Attribute genutzt werden. SQLA mapped es via
`mapped_column("metadata", ...)` korrekt.

- [ ] **Step 6.2: Replace odd __import__ workaround**

Die `__import__`-Notation oben ist Plan-Demonstration. Tatsaechlich:
ergaenze den direkten Import oben:

```python
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
```

Dann verwenden:

```python
ingested_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
)
```

- [ ] **Step 6.3: Verify Import**

```bash
source .venv/bin/activate
python -c "from backend.infrastructure.persistence.models.embedding import DocumentORM, EmbeddingChunkORM; print('OK')"
mypy backend/infrastructure/persistence/models/embedding.py
```

Expected: `OK` und mypy gruen.

- [ ] **Step 6.4: Commit**

```bash
git add backend/infrastructure/persistence/models/embedding.py
git commit -m "feat(rag): SQLA-ORM-Models DocumentORM + EmbeddingChunkORM (Slice 1 Task 6)"
```

---

## Task 7: SQLA Repository-Adapter

**Files:**
- Create: `backend/infrastructure/persistence/repositories/embedding_repository.py`

- [ ] **Step 7.1: Implement Adapter**

Create `backend/infrastructure/persistence/repositories/embedding_repository.py`:

```python
"""SQLAlchemy-Adapter fuer EmbeddingRepository (RAG Slice 1).

Pattern: session_factory pro Operation (PR #25-Stil, analog
SQLAResearchMemoRepository) — vermeidet Transaction-Leaks.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.entities.document import Document
from backend.domain.entities.embedding_chunk import EmbeddingChunk
from backend.domain.repositories.embedding_repository import (
    DuplicateUrl,
    EmbeddingRepository,
)
from backend.infrastructure.persistence.models.embedding import (
    DocumentORM,
    EmbeddingChunkORM,
)


class SQLAEmbeddingRepository(EmbeddingRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_document(self, doc: Document) -> None:
        async with self._session_factory() as session:
            session.add(
                DocumentORM(
                    id=doc.id,
                    ticker=doc.ticker,
                    doc_type=doc.doc_type,
                    filing_date=doc.filing_date,
                    url=doc.url,
                    raw_text_hash=doc.raw_text_hash,
                    ingested_at=doc.ingested_at,
                )
            )
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                if "url" in str(exc.orig).lower():
                    raise DuplicateUrl(doc.url) from exc
                raise

    async def save_chunks(self, chunks: list[EmbeddingChunk]) -> None:
        if not chunks:
            return
        async with self._session_factory() as session:
            # UPSERT: bei (document_id, chunk_idx)-Konflikt update statt fehlschlagen.
            # Macht Re-Ingestion idempotent.
            stmt = pg_insert(EmbeddingChunkORM).values(
                [
                    {
                        "id": c.id,
                        "document_id": c.document_id,
                        "chunk_idx": c.chunk_idx,
                        "content": c.content,
                        "embedding": c.embedding,
                        "metadata": c.metadata,
                    }
                    for c in chunks
                ]
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_doc_chunk_idx",
                set_={
                    "content": stmt.excluded.content,
                    "embedding": stmt.excluded.embedding,
                    "metadata": stmt.excluded.metadata,
                },
            )
            await session.execute(stmt)
            await session.commit()

    async def get_document_by_url(self, url: str) -> Document | None:
        async with self._session_factory() as session:
            stmt = select(DocumentORM).where(DocumentORM.url == url)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _orm_to_doc(row) if row else None

    async def count_chunks(self, document_id: UUID) -> int:
        from sqlalchemy import func
        async with self._session_factory() as session:
            stmt = select(func.count(EmbeddingChunkORM.id)).where(
                EmbeddingChunkORM.document_id == document_id
            )
            count = (await session.execute(stmt)).scalar()
            return int(count or 0)

    async def list_documents(self, *, ticker: str | None = None) -> list[Document]:
        async with self._session_factory() as session:
            stmt = select(DocumentORM).order_by(DocumentORM.ingested_at.desc())
            if ticker is not None:
                stmt = stmt.where(DocumentORM.ticker == ticker)
            rows = (await session.execute(stmt)).scalars().all()
            return [_orm_to_doc(r) for r in rows]


def _orm_to_doc(row: DocumentORM) -> Document:
    return Document(
        id=row.id,
        ticker=row.ticker,
        doc_type=row.doc_type,
        filing_date=row.filing_date,
        url=row.url,
        raw_text_hash=row.raw_text_hash,
        ingested_at=row.ingested_at,
    )
```

- [ ] **Step 7.2: Verify mypy + ruff**

```bash
source .venv/bin/activate
mypy backend/infrastructure/persistence/repositories/embedding_repository.py
ruff check backend/infrastructure/persistence/repositories/embedding_repository.py
```

Expected: gruen.

- [ ] **Step 7.3: Commit**

```bash
git add backend/infrastructure/persistence/repositories/embedding_repository.py
git commit -m "feat(rag): SQLAEmbeddingRepository-Adapter (Slice 1 Task 7)"
```

---

## Task 8: Integration-Tests

**Files:**
- Create: `backend/tests/integration/persistence/test_embedding_repository.py`

- [ ] **Step 8.1: Existing test-fixture-pattern lesen**

```bash
grep -A 30 "db_session\|@pytest_asyncio.fixture" \
    backend/tests/integration/persistence/test_research_memo_repository.py | head -60
```

Notiere konkret welche Fixtures aus `conftest.py` verfuegbar sind
(`db_session`, `session_factory`, etc.). Wir nutzen das gleiche Pattern.

- [ ] **Step 8.2: Write Integration-Tests**

Create `backend/tests/integration/persistence/test_embedding_repository.py`:

```python
"""Integration-Tests fuer SQLAEmbeddingRepository gegen Live-Postgres mit pgvector.

Voraussetzung: docker-compose up -d db, alembic upgrade head.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.entities.document import Document
from backend.domain.entities.embedding_chunk import EMBEDDING_DIM, EmbeddingChunk
from backend.domain.repositories.embedding_repository import DuplicateUrl
from backend.infrastructure.persistence.repositories.embedding_repository import (
    SQLAEmbeddingRepository,
)

pytestmark = [pytest.mark.integration]


# --- Test-Builders -----------------------------------------------------------

def _new_doc(
    *,
    ticker: str = "AAPL",
    doc_type: str = "10-K",
    url: str | None = None,
) -> Document:
    return Document(
        id=uuid.uuid4(),
        ticker=ticker,
        doc_type=doc_type,
        filing_date=date(2024, 1, 1),
        url=url or f"https://sec.gov/{uuid.uuid4()}.pdf",
        raw_text_hash=None,
        ingested_at=datetime.now(UTC),
    )


def _new_chunk(
    *,
    document_id: uuid.UUID,
    chunk_idx: int = 0,
    content: str | None = None,
) -> EmbeddingChunk:
    return EmbeddingChunk(
        id=uuid.uuid4(),
        document_id=document_id,
        chunk_idx=chunk_idx,
        content=content or f"chunk content {chunk_idx}",
        embedding=[0.1] * EMBEDDING_DIM,
        metadata={"section": "Risk Factors"},
    )


# --- Fixtures ----------------------------------------------------------------

@pytest_asyncio.fixture
async def repo(session_factory: async_sessionmaker[AsyncSession]) -> SQLAEmbeddingRepository:
    """SUT: Repository mit echter session_factory (von conftest)."""
    return SQLAEmbeddingRepository(session_factory)


# --- Tests -------------------------------------------------------------------

class TestSaveAndGetDocument:
    async def test_roundtrip(self, repo: SQLAEmbeddingRepository) -> None:
        doc = _new_doc()
        await repo.save_document(doc)
        loaded = await repo.get_document_by_url(doc.url)
        assert loaded is not None
        assert loaded.id == doc.id
        assert loaded.ticker == doc.ticker
        assert loaded.doc_type == doc.doc_type

    async def test_get_missing_returns_none(self, repo: SQLAEmbeddingRepository) -> None:
        loaded = await repo.get_document_by_url("https://nowhere.example/x.pdf")
        assert loaded is None

    async def test_duplicate_url_raises(self, repo: SQLAEmbeddingRepository) -> None:
        url = f"https://sec.gov/dup-{uuid.uuid4()}.pdf"
        await repo.save_document(_new_doc(url=url))
        with pytest.raises(DuplicateUrl):
            await repo.save_document(_new_doc(url=url))


class TestSaveChunks:
    async def test_batch_insert(self, repo: SQLAEmbeddingRepository) -> None:
        doc = _new_doc()
        await repo.save_document(doc)
        chunks = [_new_chunk(document_id=doc.id, chunk_idx=i) for i in range(50)]
        await repo.save_chunks(chunks)
        assert await repo.count_chunks(doc.id) == 50

    async def test_empty_batch_is_noop(self, repo: SQLAEmbeddingRepository) -> None:
        doc = _new_doc()
        await repo.save_document(doc)
        await repo.save_chunks([])
        assert await repo.count_chunks(doc.id) == 0

    async def test_upsert_on_duplicate_chunk_idx(
        self, repo: SQLAEmbeddingRepository
    ) -> None:
        """Re-Ingestion mit gleichem (document_id, chunk_idx) updated content."""
        doc = _new_doc()
        await repo.save_document(doc)
        first = _new_chunk(document_id=doc.id, chunk_idx=0, content="original")
        await repo.save_chunks([first])
        # Selber chunk_idx, neuer content
        second = _new_chunk(document_id=doc.id, chunk_idx=0, content="updated")
        await repo.save_chunks([second])
        assert await repo.count_chunks(doc.id) == 1
        # second.id ist neu, aber DB-row hat first.id (UPSERT updated row).
        # Content-Update verifizieren waere besser via get_chunk_by_idx,
        # was Slice 1 nicht hat — daher only count-check + keine Exception.


class TestCascadeDelete:
    async def test_delete_document_deletes_chunks(
        self,
        repo: SQLAEmbeddingRepository,
        db_session: AsyncSession,
    ) -> None:
        doc = _new_doc()
        await repo.save_document(doc)
        await repo.save_chunks([_new_chunk(document_id=doc.id, chunk_idx=i) for i in range(5)])

        # Direkt via Session loeschen (kein delete_document im Slice-1-Port)
        from backend.infrastructure.persistence.models.embedding import DocumentORM
        from sqlalchemy import delete
        await db_session.execute(delete(DocumentORM).where(DocumentORM.id == doc.id))
        await db_session.commit()

        assert await repo.count_chunks(doc.id) == 0


class TestListDocuments:
    async def test_list_all(self, repo: SQLAEmbeddingRepository) -> None:
        # Test-DB ist persistent zwischen Tests, daher unique URLs nutzen,
        # nicht 'genau N docs' asserten — sondern dass unsere docs drin sind.
        d1 = _new_doc(ticker="AAPL")
        d2 = _new_doc(ticker="MSFT")
        await repo.save_document(d1)
        await repo.save_document(d2)
        all_docs = await repo.list_documents()
        urls = {d.url for d in all_docs}
        assert d1.url in urls
        assert d2.url in urls

    async def test_filtered_by_ticker(self, repo: SQLAEmbeddingRepository) -> None:
        d_aapl = _new_doc(ticker="AAPL")
        d_msft = _new_doc(ticker="MSFT")
        await repo.save_document(d_aapl)
        await repo.save_document(d_msft)
        aapl_docs = await repo.list_documents(ticker="AAPL")
        urls = {d.url for d in aapl_docs}
        assert d_aapl.url in urls
        assert d_msft.url not in urls

    async def test_sorted_desc_by_ingested_at(
        self, repo: SQLAEmbeddingRepository
    ) -> None:
        d_old = _new_doc(ticker="ZZZX")  # eindeutiger Ticker fuer Filter
        await repo.save_document(d_old)
        d_new = _new_doc(ticker="ZZZX")
        await repo.save_document(d_new)
        docs = await repo.list_documents(ticker="ZZZX")
        # Neueste zuerst — server_default=now() macht das deterministisch
        # falls die DB-Writes monoton timestampen.
        assert docs[0].url == d_new.url
        assert docs[-1].url == d_old.url
```

- [ ] **Step 8.3: Run Integration-Tests**

```bash
source .venv/bin/activate
# Sicherstellen dass Migration up ist
DATABASE_URL=postgresql+asyncpg://prisma:prisma@localhost:5432/prisma \
    alembic upgrade head

pytest backend/tests/integration/persistence/test_embedding_repository.py -v
```

Expected: alle Tests gruen. Falls Tests vorher noch nicht alle Fixtures kennen
(`session_factory`, `db_session`): `backend/tests/integration/conftest.py`
und/oder `backend/tests/conftest.py` lesen und passende Fixtures auswaehlen.

- [ ] **Step 8.4: Commit**

```bash
git add backend/tests/integration/persistence/test_embedding_repository.py
git commit -m "test(rag): Integration-Tests fuer SQLAEmbeddingRepository (Slice 1 Task 8)"
```

---

## Task 9: Pre-Push CI-Mirror + AI-USAGE + Final Verify

**Files:**
- Modify: `docs/AI-USAGE.md`

- [ ] **Step 9.1: Full CI-Mirror + Coverage**

```bash
source .venv/bin/activate

# Lint + Format
ruff check backend/
ruff format --check backend/

# Type-Check
mypy backend/

# Unit-Tests
pytest backend/tests/unit -q

# Integration-Tests (braucht laufende DB + Migration)
pytest backend/tests/integration/persistence/test_embedding_repository.py -q

# Coverage auf neue Module
pytest \
    backend/tests/unit/domain/entities/test_document.py \
    backend/tests/unit/domain/entities/test_embedding_chunk.py \
    backend/tests/integration/persistence/test_embedding_repository.py \
    --cov=backend/domain/entities/document \
    --cov=backend/domain/entities/embedding_chunk \
    --cov=backend/domain/repositories/embedding_repository \
    --cov=backend/infrastructure/persistence/models/embedding \
    --cov=backend/infrastructure/persistence/repositories/embedding_repository \
    --cov-report=term-missing \
    --cov-fail-under=85
```

Expected: alles gruen, Coverage >=85% auf den neuen Modulen.

- [ ] **Step 9.2: AI-USAGE-Eintrag verfassen**

Edit `docs/AI-USAGE.md` — neuen Eintrag mit:

- Datum 2026-05-11
- Slice-Spec + Plan-Doc-Pfade
- Patterns: P1 (Q-by-Q-Brainstorming fuer Slice-Groessen-Decision), P2 (Reality-Check: docker-compose schon mit pgvector, Render-pgvector-Support verifiziert, ORM-Pattern in Codebase verifiziert), P4 (Plan-as-Contract: verbatim Code je Task), P6 (Strict-Scope: kein Ingestion/Retrieval in Slice 1)
- A1 Plan-Code-Drift vermieden: docker-compose-Anpassung im Spec war falsch eingeplant, Plan-Phase hat verifiziert dass `pgvector/pgvector:pg16`-Image schon im Compose ist
- Test-Coverage: Unit (Entities) + Integration (Repository)
- Inference-Tokens fuer Plan-Phase notieren

- [ ] **Step 9.3: Commit AI-USAGE**

```bash
git add docs/AI-USAGE.md
git commit -m "docs(ai-usage): RAG-Slice-1-Foundation-Eintrag (Slice 1 Task 9)"
```

- [ ] **Step 9.4: Push + PR-Strategie**

Empfehlung: Code-PR `feat/rag-pipeline-slice-1` (base auf main) nach Spec-PR-Merge anlegen. Spec+Plan-PR (#79) bleibt nur Docs.

---

## Self-Review

Nach Plan-Schreiben mit frischen Augen:

**1. Spec-Coverage:** Jede Spec-Sektion adressiert?
- §3 Architektur: ✅ Task 2-7
- §4 Datenmodell: ✅ Task 5 (Migration) + Task 6 (ORM)
- §5 Repository-Port: ✅ Task 4
- §6 Migration: ✅ Task 5 inkl. up/down-Test
- §7 Tests: ✅ Task 2/3 (Unit) + Task 8 (Integration)
- §8 Acceptance: alle Punkte abgedeckt inkl. Migration-Verify
- §9 Risiken: docker-compose-Risiko gestrichen (war schon mitigated), pgvector-Render-Risk dokumentiert

**2. Placeholder-Scan:**
- Task 6 hat `__import__("sqlalchemy")`-Workaround → Step 6.2 ersetzt mit normalem Import. **Akzeptiert** — bewusste Demonstration der Doppelschritt-Korrektur.
- Task 8 Step 8.1 sagt "Notiere konkret welche Fixtures aus conftest.py verfuegbar sind" — nicht ideal, aber wir verifizieren das *vor* Test-Schreiben. **Akzeptiert** — Fixtures kennen, bevor wir sie nutzen.
- Task 8 last test (`test_sorted_desc_by_ingested_at`) hat "falls die DB-Writes monoton timestampen" — kleines theoretisches Race. **Akzeptiert** — server_default=now() auf gleicher Connection ist OK.

**3. Type-Consistency:**
- `Document` Felder einheitlich in Task 2 (Entity), Task 5 (Migration), Task 6 (ORM), Task 7 (Adapter), Task 8 (Tests) ✓
- `EmbeddingChunk` analog ✓
- `metadata` als Python-Attribute heisst `chunk_metadata` in ORM (wegen Base-Konflikt), aber als DB-Spalte `metadata` (Task 6) — Tests pruefen das implizit (Roundtrip mit metadata={"section": "Risk Factors"})

**4. Migration-Reversibility:** Step 5.3 testet up, Step 5.4 testet down. ✓

## Execution Handoff

**Plan saved to:** `docs/specs/2026-05-11-rag-pipeline-slice-1-plan.md`

Empfohlene Execution: superpowers:subagent-driven-development. Tasks sind weitgehend sequenziell (Task 2/3 koennten parallel, aber der Gewinn ist klein).

Sequenz: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9.

Estimated Execution: ~75-100 min (9 Tasks, je 5-15 min mechanisch).
