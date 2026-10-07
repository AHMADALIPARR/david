"""Execute only the sparse-selected agent set — no swarm fan-out."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from .models import AgentResult, EvidenceBundle, WorkItem

# Handler: (WorkItem) -> AgentResult
AgentHandler = Callable[[WorkItem], AgentResult]


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    task: str
    evidence_bundle: EvidenceBundle
    required_outputs: tuple[str, ...]
    permissions: frozenset[str]
    risk_policy: str
    deadline: str | None = None


def build_work_items(
    selected_agent_ids: Sequence[str],
    req: ExecutionRequest,
) -> list[WorkItem]:
    """One WorkItem per selected agent_id. Order preserved. No extras."""
    if not selected_agent_ids:
        return []
    # Deduplicate while preserving order (router may close deps + control plane).
    seen: set[str] = set()
    ordered: list[str] = []
    for aid in selected_agent_ids:
        if aid not in seen:
            seen.add(aid)
            ordered.append(aid)
    return [
        WorkItem(
            request_id=req.request_id,
            work_id=f"{req.request_id}:{aid}:{uuid.uuid4().hex[:8]}",
            agent_id=aid,
            task=req.task,
            evidence_bundle=req.evidence_bundle,
            required_outputs=req.required_outputs,
            permissions=req.permissions,
            deadline=req.deadline,
            risk_policy=req.risk_policy,
        )
        for aid in ordered
    ]


def dispatch(
    selected_agent_ids: Sequence[str],
    req: ExecutionRequest,
    handlers: Mapping[str, AgentHandler],
    *,
    allow_missing: bool = False,
) -> list[AgentResult]:
    """
    Run handlers only for selected agents.

    Agents not in selected_agent_ids are never invoked.
    Missing handlers raise KeyError unless allow_missing (then status=skipped).
    """
    items = build_work_items(selected_agent_ids, req)
    results: list[AgentResult] = []
    for item in items:
        handler = handlers.get(item.agent_id)
        if handler is None:
            if not allow_missing:
                raise KeyError(f"no handler for selected agent {item.agent_id!r}")
            results.append(
                AgentResult(agent_id=item.agent_id, status="skipped")
            )
            continue
        results.append(handler(item))
    return results


def stub_handler(agent_id: str) -> AgentHandler:
    """Deterministic stub for wiring tests (not a real agent)."""

    def _run(item: WorkItem) -> AgentResult:
        assert item.agent_id == agent_id
        return AgentResult(
            agent_id=agent_id,
            conclusions=({"note": f"stub:{agent_id}", "work_id": item.work_id},),
            evidence_refs=tuple(
                e.evidence_id for e in item.evidence_bundle.sources
            ),
            provenance_root=f"prov:{item.request_id}:{agent_id}",
            status="ok",
        )

    return _run
