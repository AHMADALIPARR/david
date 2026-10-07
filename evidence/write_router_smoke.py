"""Append a router smoke log line using frozen scorer + Spec symbolic.

Does not modify router/scorer.py or router/symbolic.py.
Scores come only from scorer.score_agent (via symbolic.minimum_agent_set).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# David root on path so `evidence` and `router` imports resolve
DAVID_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAVID_ROOT))
sys.path.insert(0, str(DAVID_ROOT / "router"))

from scorer import AgentDescriptor, RequestContext, score_agent  # noqa: E402
from symbolic import minimum_agent_set  # noqa: E402

from evidence.retrieve import (  # noqa: E402
    COBOL_BALANCE_QUERY,
    COBOL_BALANCE_QUERY_VEC,
    EvidenceIndex,
    retrieve,
    seed_cobol_corpus,
)

LOG_PATH = DAVID_ROOT / "logs" / "router_smoke.log"


def _agent(aid, caps, deps=(), control=False, risk="medium", perms=(), inputs=()):
    """Same helper shape as router/test_scorer.py."""
    return AgentDescriptor(
        agent_id=aid,
        domain="test",
        capabilities=frozenset(caps),
        input_types=frozenset(inputs or ("source_code",)),
        permissions=frozenset(perms or ("read_source",)),
        risk_class=risk,
        dependencies=frozenset(deps),
        historical_success=0.5,
        control_plane=control,
    )


def cobol_request_context():
    """COBOL-style RequestContext from router/test_scorer.py."""
    registry = {
        "LegacyCobol": _agent(
            "LegacyCobol",
            ["cobol", "business_rule_extraction"],
            deps=("Database", "Provenance"),
            risk="high",
        ),
        "Database": _agent("Database", ["schema_analysis"], inputs=("db_schema",)),
        "Provenance": _agent("Provenance", ["provenance_dag"]),
        "Quant": _agent("Quant", ["pricing", "monte_carlo"]),
        "Risk": _agent("Risk", ["risk_policy"], control=True, risk="critical"),
        "Response": _agent("Response", ["synthesis"], control=True),
    }
    candidates = list(registry.values())
    req = RequestContext(
        required_capabilities=frozenset({"cobol", "business_rule_extraction"}),
        available_inputs=frozenset({"source_code", "copybooks"}),
        granted_permissions=frozenset({"read_source", "read_copybooks"}),
        max_risk_class="high",
        semantic_scores={
            "LegacyCobol": 0.92,
            "Database": 0.4,
            "Quant": 0.1,
            "Provenance": 0.3,
            "Risk": 0.2,
            "Response": 0.2,
        },
    )
    return registry, candidates, req


def write_smoke_log(path: Path | None = None) -> Path:
    log_path = path or LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    registry, candidates, req = cobol_request_context()
    # Prefer Spec's minimum_agent_set (uses scorer.score_agent only)
    selected = minimum_agent_set(candidates, req, registry)
    # Touch score_agent explicitly so the smoke note is accurate
    _ = {a.agent_id: score_agent(a, req) for a in candidates}

    bundle = retrieve(
        COBOL_BALANCE_QUERY,
        query_embedding=COBOL_BALANCE_QUERY_VEC,
        index=EvidenceIndex(seed_cobol_corpus()),
        min_authority=0.5,
        require_parent_evidence=True,
        top_k=5,
    )
    top_eids = [s["evidence_id"] for s in bundle["sources"]]

    # Timestamp in America/Los_Angeles for operator-facing logs
    try:
        from zoneinfo import ZoneInfo

        ts = datetime.now(ZoneInfo("America/Los_Angeles")).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )
    except Exception:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    quant_absent = "Quant" not in selected
    risk_present = "Risk" in selected
    response_present = "Response" in selected

    lines = [
        f"[{ts}] router_smoke minimum_agent_set selected={selected}",
        f"[{ts}] Quant absent={quant_absent}; Risk present={risk_present}; "
        f"Response present={response_present}",
        f"[{ts}] note: scores came from scorer.score_agent only "
        f"(via symbolic.minimum_agent_set; no second scorer)",
        f"[{ts}] evidence_smoke query={COBOL_BALANCE_QUERY!r} "
        f"top_evidence_ids={top_eids}",
        "",
    ]

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return log_path


if __name__ == "__main__":
    out = write_smoke_log()
    print(f"appended router smoke log → {out}")
