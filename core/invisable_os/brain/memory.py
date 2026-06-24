"""The Brain: a thin semantic-memory abstraction over ChromaDB with a local fallback.

Memories are namespaced by ``kind`` (e.g. ``"winning_pattern"``,
``"performance_learning"``, ``"trend_signal"``, ``"cultural_note"``) so each engine
can store and recall its own class of knowledge while still sharing one substrate.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from invisable_os.config import Settings, get_settings

log = logging.getLogger(__name__)

COLLECTION = "invisable_brain"


@dataclass
class Memory:
    """A single unit of remembered knowledge."""

    text: str
    kind: str = "note"
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


class Brain:
    """Shared memory. Prefers ChromaDB; falls back to an in-memory keyword store."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._chroma = None
        self._collection = None
        self._local: list[Memory] = []
        self._connect()

    def _connect(self) -> None:
        try:
            import chromadb  # optional dependency

            self._chroma = chromadb.HttpClient(
                host=self.settings.chroma_host, port=self.settings.chroma_port
            )
            self._collection = self._chroma.get_or_create_collection(COLLECTION)
            log.info("Brain connected to ChromaDB at %s", self.settings.chroma_host)
        except Exception as exc:  # noqa: BLE001 — fall back gracefully
            log.info("Brain using in-memory store (ChromaDB unavailable): %s", exc)
            self._chroma = None

    # -- writing -------------------------------------------------------------

    def remember(self, memory: Memory) -> str:
        """Persist a memory; returns its id."""
        if self._collection is not None:
            try:
                self._collection.add(
                    ids=[memory.id],
                    documents=[memory.text],
                    metadatas=[{"kind": memory.kind, **memory.metadata}],
                )
                return memory.id
            except Exception as exc:  # noqa: BLE001
                log.warning("Brain write to ChromaDB failed, using local: %s", exc)
        self._local.append(memory)
        return memory.id

    def remember_text(self, text: str, kind: str = "note", **metadata) -> str:
        return self.remember(Memory(text=text, kind=kind, metadata=metadata))

    # -- recall --------------------------------------------------------------

    def recall(self, query: str, *, kind: str | None = None, limit: int = 5) -> list[Memory]:
        """Return memories most relevant to ``query`` (optionally filtered by kind)."""
        if self._collection is not None:
            try:
                where = {"kind": kind} if kind else None
                res = self._collection.query(
                    query_texts=[query], n_results=limit, where=where
                )
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                ids = (res.get("ids") or [[]])[0]
                return [
                    Memory(text=d, kind=(m or {}).get("kind", "note"), metadata=m or {}, id=i)
                    for d, m, i in zip(docs, metas, ids, strict=False)
                ]
            except Exception as exc:  # noqa: BLE001
                log.warning("Brain recall from ChromaDB failed, using local: %s", exc)

        # Local fallback: simple keyword overlap ranking.
        pool = [m for m in self._local if kind is None or m.kind == kind]
        terms = {t for t in query.lower().split() if len(t) > 2}
        ranked = sorted(
            pool,
            key=lambda m: len(terms & set(m.text.lower().split())),
            reverse=True,
        )
        return ranked[:limit]

    def count(self, kind: str | None = None) -> int:
        if self._collection is not None:
            try:
                if kind:
                    return len(self._collection.get(where={"kind": kind}).get("ids", []))
                return self._collection.count()
            except Exception:  # noqa: BLE001
                pass
        return len([m for m in self._local if kind is None or m.kind == kind])


_singleton: Brain | None = None


def get_brain() -> Brain:
    """Return the process-wide Brain singleton."""
    global _singleton
    if _singleton is None:
        _singleton = Brain()
    return _singleton
