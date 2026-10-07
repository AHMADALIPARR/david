"""Hybrid evidence retrieval — dense + lexical + metadata + provenance.

In-memory stand-in for sql/001_agent_and_evidence_indexes.sql.
Production SQL uses vector(1536); tests use fixed dim-8 vectors (no live DB).

Merge / rerank rule (deterministic):
  score = dense_cosine + lexical_overlap + source_authority - penalties
  sort by (-score, evidence_id)
  penalties: missing required parent_evidence when policy requires it

Hybrid note: a chunk with weak dense but strong lexical can still rank
if lexical_overlap compensates (no hard dense floor).
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


# Production pgvector column is vector(1536); test corpus uses tiny fixed vectors.
EMBEDDING_DIM_TEST = 8
EMBEDDING_DIM_PRODUCTION = 1536


@dataclass
class EvidenceRecord:
    """Fields mirror the SQL ``evidence`` table."""

    evidence_id: str
    source_id: str
    source_type: str
    document_id: str | None
    location: str | None
    content: str
    content_hash: str
    embedding: list[float] | None
    source_authority: float = 0.5
    parent_evidence: tuple[str, ...] = ()
    created_at: str | None = None


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def lexical_score(query: str, content: str) -> float:
    """Token overlap stand-in for ``content_tsv @@ plainto_tsquery``."""
    q = _tokenize(query)
    if not q:
        return 0.0
    c = _tokenize(content)
    if not c:
        return 0.0
    return len(q & c) / len(q)


def empty_bundle() -> dict[str, Any]:
    """EvidenceBundle-shaped dict with no hits (contracts.md)."""
    return {
        "facts": [],
        "sources": [],
        "provenance": [],
        "retrieval_metadata": [],
    }


def seed_cobol_corpus() -> list[EvidenceRecord]:
    """Fixed COBOL-modernization corpus (dim-8 embeddings for tests).

    Axes (approx): [cobol, balance, payment, schema, pricing, vol, greek, junk]
    """
    # Strong COBOL / balance / payment cluster
    copybook = EvidenceRecord(
        evidence_id="ev_copybook_01",
        source_id="src_copybook_acct",
        source_type="copybook",
        document_id="ACCTREC.cpy",
        location="01-ACCOUNT-BALANCE",
        content=(
            "01 ACCOUNT-RECORD. "
            "05 ACCOUNT-BALANCE PIC S9(9)V99. "
            "05 PAYMENT-AMOUNT PIC S9(7)V99. "
            "05 LAST-PAYMENT-DATE PIC X(8)."
        ),
        content_hash="",
        embedding=[0.95, 0.90, 0.85, 0.20, 0.05, 0.0, 0.0, 0.0],
        source_authority=0.95,
        parent_evidence=("ev_provenance_root",),
        created_at="2026-01-01T00:00:00Z",
    )
    cobol_src = EvidenceRecord(
        evidence_id="ev_cobol_src_01",
        source_id="src_cobol_pay",
        source_type="cobol_source",
        document_id="PAYROLL.cbl",
        location="PROCEDURE DIVISION / CALC-BALANCE",
        content=(
            "COMPUTE ACCOUNT-BALANCE = ACCOUNT-BALANCE - PAYMENT-AMOUNT. "
            "IF ACCOUNT-BALANCE < ZERO THEN PERFORM OVERDRAFT-CHECK. "
            "MOVE PAYMENT-AMOUNT TO WS-LAST-PAYMENT."
        ),
        content_hash="",
        embedding=[0.92, 0.88, 0.90, 0.15, 0.05, 0.0, 0.0, 0.0],
        source_authority=0.90,
        parent_evidence=("ev_provenance_root",),
        created_at="2026-01-01T00:00:00Z",
    )
    db2 = EvidenceRecord(
        evidence_id="ev_db2_schema_01",
        source_id="src_db2_acct",
        source_type="db2_schema",
        document_id="ACCT.DDL",
        location="TABLE ACCOUNT_BALANCES",
        content=(
            "CREATE TABLE ACCOUNT_BALANCES ("
            "ACCT_ID CHAR(12), BALANCE DECIMAL(11,2), "
            "LAST_PAYMENT DECIMAL(9,2), UPDATED_TS TIMESTAMP)."
        ),
        content_hash="",
        embedding=[0.70, 0.80, 0.55, 0.95, 0.05, 0.0, 0.0, 0.0],
        source_authority=0.85,
        parent_evidence=("ev_provenance_root",),
        created_at="2026-01-01T00:00:00Z",
    )
    # Should NOT win on a COBOL balance query (pricing / quant cluster)
    quant = EvidenceRecord(
        evidence_id="ev_quant_pricing_01",
        source_id="src_quant_report",
        source_type="quant_report",
        document_id="PRICING_Q3.pdf",
        location="section:monte_carlo",
        content=(
            "Monte Carlo pricing of exotic options. "
            "Implied volatility surface and greek sensitivities. "
            "No COBOL or account balance fields."
        ),
        content_hash="",
        embedding=[0.05, 0.05, 0.05, 0.05, 0.95, 0.90, 0.85, 0.10],
        source_authority=0.80,
        parent_evidence=("ev_provenance_root",),
        created_at="2026-01-01T00:00:00Z",
    )
    # Low-authority junk for provenance filter tests
    junk = EvidenceRecord(
        evidence_id="ev_junk_lowauth_01",
        source_id="src_web_scrape",
        source_type="web_scrape",
        document_id="random-blog.html",
        location="body",
        content=(
            "Someone said COBOL payment balance might work like a spreadsheet. "
            "Unverified forum post."
        ),
        content_hash="",
        embedding=[0.60, 0.55, 0.50, 0.10, 0.10, 0.0, 0.0, 0.9],
        source_authority=0.15,
        parent_evidence=(),
        created_at="2026-01-01T00:00:00Z",
    )
    # Weak dense (far from COBOL cluster) but strong lexical on balance/payment/cobol
    # — hybrid: lexical can lift it into results when dense alone would not.
    lexical_lift = EvidenceRecord(
        evidence_id="ev_lexical_lift_01",
        source_id="src_glossary",
        source_type="glossary",
        document_id="LEGACY-GLOSSARY.txt",
        location="entry:PAYMENT-BALANCE",
        content=(
            "cobol payment balance glossary entry: "
            "PAYMENT and BALANCE fields on ACCOUNT records in legacy batch."
        ),
        content_hash="",
        # Oriented away from COBOL cluster → weak cosine vs COBOL query
        embedding=[0.10, 0.15, 0.10, 0.05, 0.40, 0.35, 0.30, 0.20],
        source_authority=0.70,
        parent_evidence=("ev_provenance_root",),
        created_at="2026-01-01T00:00:00Z",
    )

    records = [copybook, cobol_src, db2, quant, junk, lexical_lift]
    for r in records:
        r.content_hash = _content_hash(r.content)
    return records


# Canonical COBOL payment/balance query embedding (dim 8)
COBOL_BALANCE_QUERY = "cobol account payment balance CALC-BALANCE"
COBOL_BALANCE_QUERY_VEC = [0.93, 0.91, 0.88, 0.25, 0.05, 0.0, 0.0, 0.0]


@dataclass
class EvidenceIndex:
    """In-memory evidence index (no Postgres required)."""

    records: list[EvidenceRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.records:
            self.records = seed_cobol_corpus()
        self._by_id = {r.evidence_id: r for r in self.records}

    def add(self, record: EvidenceRecord) -> None:
        if not record.content_hash:
            record.content_hash = _content_hash(record.content)
        self.records.append(record)
        self._by_id[record.evidence_id] = record


def retrieve(
    query: str,
    *,
    query_embedding: Sequence[float] | None = None,
    index: EvidenceIndex | None = None,
    source_types: Iterable[str] | None = None,
    document_ids: Iterable[str] | None = None,
    min_authority: float = 0.0,
    require_parent_evidence: bool = False,
    top_k: int = 10,
) -> dict[str, Any]:
    """Hybrid retrieve → EvidenceBundle-shaped dict (facts/sources/provenance/…).

    Agents never receive bare text without provenance fields on each source.
    """
    if not query or not query.strip():
        return empty_bundle()

    idx = index or EvidenceIndex()
    st_filter = set(source_types) if source_types is not None else None
    doc_filter = set(document_ids) if document_ids is not None else None
    q_emb = list(query_embedding) if query_embedding is not None else None

    scored: list[tuple[float, EvidenceRecord, dict[str, float]]] = []
    for rec in idx.records:
        # Metadata filters
        if st_filter is not None and rec.source_type not in st_filter:
            continue
        if doc_filter is not None and rec.document_id not in doc_filter:
            continue
        # Provenance / authority
        if rec.source_authority < min_authority:
            continue
        if require_parent_evidence and not rec.parent_evidence:
            continue

        dense = 0.0
        if q_emb is not None and rec.embedding is not None:
            dense = cosine_similarity(q_emb, rec.embedding)
        lex = lexical_score(query, rec.content)
        authority = float(rec.source_authority)
        penalty = 0.0
        if require_parent_evidence and not rec.parent_evidence:
            penalty += 1.0  # defensive; already filtered above

        score = dense + lex + authority - penalty
        parts = {
            "dense": dense,
            "lexical": lex,
            "source_authority": authority,
            "penalty": penalty,
            "score": score,
        }
        scored.append((score, rec, parts))

    # Deterministic rerank: score desc, then evidence_id asc
    scored.sort(key=lambda t: (-t[0], t[1].evidence_id))
    top = scored[:top_k]

    if not top:
        return empty_bundle()

    facts: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    retrieval_metadata: list[dict[str, Any]] = []

    for score, rec, parts in top:
        facts.append(
            {
                "evidence_id": rec.evidence_id,
                "summary": rec.content[:160],
                "source_type": rec.source_type,
            }
        )
        sources.append(
            {
                "evidence_id": rec.evidence_id,
                "source_id": rec.source_id,
                "source_type": rec.source_type,
                "document_id": rec.document_id,
                "location": rec.location,
                "content_hash": rec.content_hash,
                "source_authority": rec.source_authority,
                "parent_evidence": list(rec.parent_evidence),
                "content": rec.content,
                "retrieval_score": score,
            }
        )
        provenance.append(
            {
                "evidence_id": rec.evidence_id,
                "source_id": rec.source_id,
                "content_hash": rec.content_hash,
                "parent_evidence": list(rec.parent_evidence),
                "source_authority": rec.source_authority,
            }
        )
        retrieval_metadata.append(
            {
                "evidence_id": rec.evidence_id,
                "dense": parts["dense"],
                "lexical": parts["lexical"],
                "source_authority": parts["source_authority"],
                "penalty": parts["penalty"],
                "score": parts["score"],
                "embedding_dim_note": (
                    f"test vectors dim={EMBEDDING_DIM_TEST}; "
                    f"production SQL uses vector({EMBEDDING_DIM_PRODUCTION})"
                ),
            }
        )

    return {
        "facts": facts,
        "sources": sources,
        "provenance": provenance,
        "retrieval_metadata": retrieval_metadata,
    }
