"""Deterministic sparse-MoA agent scoring (no LLM in the selection loop)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


WEIGHTS = {
    "semantic_similarity": 1.0,
    "capability_match": 1.2,
    "input_match": 1.0,
    "historical_success": 0.8,
    "dependency_coverage": 0.6,
    "risk_penalty": 0.9,
    "permission_penalty": 1.5,
    "unnecessary_agent_penalty": 0.7,
}

RISK_PENALTY = {"low": 0.0, "medium": 0.15, "high": 0.35, "critical": 0.55}


@dataclass(frozen=True)
class AgentDescriptor:
    agent_id: str
    domain: str
    capabilities: frozenset[str]
    input_types: frozenset[str]
    permissions: frozenset[str]
    risk_class: str
    dependencies: frozenset[str]
    historical_success: float = 0.0
    control_plane: bool = False


@dataclass(frozen=True)
class RequestContext:
    required_capabilities: frozenset[str]
    available_inputs: frozenset[str]
    granted_permissions: frozenset[str]
    max_risk_class: str = "high"
    semantic_scores: dict[str, float] = field(default_factory=dict)


_RISK_ORDER = ("low", "medium", "high", "critical")


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def risk_exceeds(agent_risk: str, max_risk: str) -> bool:
    """True if agent_risk is strictly above max_risk (low < medium < high < critical)."""
    return _RISK_ORDER.index(agent_risk) > _RISK_ORDER.index(max_risk)


def _risk_exceeds(agent_risk: str, max_risk: str) -> bool:
    return risk_exceeds(agent_risk, max_risk)


def score_agent(agent: AgentDescriptor, req: RequestContext) -> float:
    """score = Σ positive terms − penalties. Higher is better."""
    sem = req.semantic_scores.get(agent.agent_id, 0.0)
    cap = _jaccard(agent.capabilities, req.required_capabilities)
    inp = _jaccard(agent.input_types, req.available_inputs)
    hist = max(0.0, min(1.0, agent.historical_success))
    # Dependency coverage: fraction of deps present in semantic top pool (caller may refine).
    dep_cov = 1.0 if not agent.dependencies else 0.5

    missing_perms = agent.permissions - req.granted_permissions
    perm_pen = 1.0 if missing_perms else 0.0
    risk_pen = RISK_PENALTY.get(agent.risk_class, 0.5)
    if _risk_exceeds(agent.risk_class, req.max_risk_class):
        risk_pen += 1.0

    # Mild penalty if the agent shares no required capabilities (unnecessary).
    unnecessary = 0.0 if cap > 0.0 or agent.control_plane else 1.0

    return (
        WEIGHTS["semantic_similarity"] * sem
        + WEIGHTS["capability_match"] * cap
        + WEIGHTS["input_match"] * inp
        + WEIGHTS["historical_success"] * hist
        + WEIGHTS["dependency_coverage"] * dep_cov
        - WEIGHTS["risk_penalty"] * risk_pen
        - WEIGHTS["permission_penalty"] * perm_pen
        - WEIGHTS["unnecessary_agent_penalty"] * unnecessary
    )


def dependency_closure(
    selected: Iterable[str],
    registry: dict[str, AgentDescriptor],
) -> list[str]:
    """Expand selected agents with required dependencies (deterministic BFS)."""
    out: list[str] = []
    seen: set[str] = set()
    queue = list(selected)
    while queue:
        aid = queue.pop(0)
        if aid in seen:
            continue
        seen.add(aid)
        out.append(aid)
        agent = registry.get(aid)
        if agent is None:
            continue
        for dep in sorted(agent.dependencies):
            if dep not in seen:
                queue.append(dep)
    return out


def select_minimum_set(
    candidates: list[AgentDescriptor],
    req: RequestContext,
    registry: dict[str, AgentDescriptor],
    top_k: int = 20,
    include_control_plane: bool = True,
) -> list[str]:
    """
    Pipeline: score → sort deterministically → top-K → dependency closure
    → optional control-plane agents → return agent_ids.
    """
    ranked = sorted(
        candidates,
        key=lambda a: (-score_agent(a, req), a.agent_id),
    )[:top_k]

    # Keep agents that match at least one required capability (or control plane later).
    core = [
        a.agent_id
        for a in ranked
        if a.capabilities & req.required_capabilities
    ]
    closed = dependency_closure(core, registry)

    if include_control_plane:
        for a in candidates:
            if a.control_plane and a.agent_id not in closed:
                closed.append(a.agent_id)

    return closed
