"""WorkItem / AgentResult / EvidenceBundle contracts for sparse execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_id: str
    source_type: str
    document_id: str
    location: str
    content_hash: str
    embedding_id: str | None = None
    retrieved_by: str | None = None
    retrieval_score: float | None = None
    source_authority: str | None = None
    timestamp: str | None = None
    parent_evidence: tuple[str, ...] = ()
    content: str | None = None  # never delivered without the fields above


@dataclass(frozen=True)
class EvidenceBundle:
    facts: tuple[dict[str, Any], ...] = ()
    sources: tuple[Evidence, ...] = ()
    provenance: tuple[dict[str, Any], ...] = ()
    retrieval_metadata: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class WorkItem:
    request_id: str
    work_id: str
    agent_id: str
    task: str
    evidence_bundle: EvidenceBundle
    required_outputs: tuple[str, ...]
    permissions: frozenset[str]
    deadline: str | None
    risk_policy: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["permissions"] = sorted(self.permissions)
        return d


@dataclass(frozen=True)
class AgentResult:
    agent_id: str
    facts: tuple[dict[str, Any], ...] = ()
    conclusions: tuple[dict[str, Any], ...] = ()
    assumptions: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    transformations: tuple[dict[str, Any], ...] = ()
    risk_signals: tuple[str, ...] = ()
    provenance_root: str | None = None
    status: str = "ok"  # ok | failed | escalated | skipped

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
