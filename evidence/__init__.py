"""In-memory evidence retrieval (mirrors sql/001 hybrid sketch; no live DB)."""

from .retrieve import (
    EvidenceRecord,
    EvidenceIndex,
    retrieve,
    seed_cobol_corpus,
    empty_bundle,
)

__all__ = [
    "EvidenceRecord",
    "EvidenceIndex",
    "retrieve",
    "seed_cobol_corpus",
    "empty_bundle",
]
