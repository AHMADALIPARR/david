"""Symbolic hard filters and minimum-agent constraint set (Spec / Hilbert).

Hard filters are predicates (True/False), not soft score penalties.
Scorer remains source of truth for scores — import score_agent / dependency_closure;
never redefine WEIGHTS or score_agent.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from scorer import (
    AgentDescriptor,
    RequestContext,
    dependency_closure,
    risk_exceeds,
    score_agent,
)


def capability_eligible(agent: AgentDescriptor, req: RequestContext) -> bool:
    """Agent shares at least one required capability, or is control-plane."""
    if agent.control_plane:
        return True
    return bool(agent.capabilities & req.required_capabilities)


def permission_eligible(agent: AgentDescriptor, req: RequestContext) -> bool:
    """Agent permissions must be a subset of granted permissions."""
    return agent.permissions <= req.granted_permissions


def risk_eligible(agent: AgentDescriptor, req: RequestContext) -> bool:
    """Agent risk_class must not exceed req.max_risk_class."""
    return not risk_exceeds(agent.risk_class, req.max_risk_class)


def apply_symbolic_filters(
    candidates: Iterable[AgentDescriptor],
    req: RequestContext,
) -> list[AgentDescriptor]:
    """Return agents that pass capability, permission, and risk hard filters."""
    return [
        a
        for a in candidates
        if capability_eligible(a, req)
        and permission_eligible(a, req)
        and risk_eligible(a, req)
    ]


def _greedy_cover(
    eligible: Sequence[AgentDescriptor],
    req: RequestContext,
) -> list[str]:
    """Greedy set-cover over required_capabilities (deterministic)."""
    uncovered = set(req.required_capabilities)
    remaining = list(eligible)
    picked: list[str] = []
    scores = {a.agent_id: score_agent(a, req) for a in remaining}

    while uncovered and remaining:
        # Primary: most still-uncovered caps; secondary: highest score; tertiary: agent_id
        def key(a: AgentDescriptor) -> tuple:
            cover = len(a.capabilities & uncovered)
            return (-cover, -scores[a.agent_id], a.agent_id)

        best = min(remaining, key=key)
        cover = len(best.capabilities & uncovered)
        if cover == 0:
            break
        picked.append(best.agent_id)
        uncovered -= best.capabilities
        remaining = [a for a in remaining if a.agent_id != best.agent_id]

    return picked


def _closure_passes_hard_filters(
    agent_id: str,
    req: RequestContext,
    registry: dict[str, AgentDescriptor],
) -> bool:
    """True iff agent_id and all transitive deps pass permission + risk.

    capability_eligible is waived for pure dependency agents pulled in solely
    as deps (they need not intersect required_capabilities).
    """
    for cid in dependency_closure([agent_id], registry):
        agent = registry.get(cid)
        if agent is None:
            return False
        if not permission_eligible(agent, req):
            return False
        if not risk_eligible(agent, req):
            return False
    return True


def minimum_agent_set(
    candidates: list[AgentDescriptor],
    req: RequestContext,
    registry: dict[str, AgentDescriptor],
    top_k: int = 20,
    mandatory_control_plane: Sequence[str] = ("Risk", "Response"),
) -> list[str]:
    """
    Hard-filter + greedy cover + dependency closure + mandatory control plane.

    Order: greedy picks, then closure BFS order, then mandatory control plane
    in the given order. Unique and stable.

    After closure, every agent must pass permission_eligible and risk_eligible.
    capability_eligible is waived for pure dependency agents. If a dependency
    fails those hard filters, its parent is ineligible — that parent and its
    incomplete closure are dropped.

    Mandatory control-plane agents skip the risk filter (matching scorer
    include_control_plane) but still require permission_eligible.
    """
    # 1–2. Score, sort deterministically, take top_k
    ranked = sorted(
        candidates,
        key=lambda a: (-score_agent(a, req), a.agent_id),
    )[:top_k]

    # 3. Hard filters on the pool
    eligible = apply_symbolic_filters(ranked, req)

    # 4. Greedy set-cover
    greedy_ids = _greedy_cover(eligible, req)

    # 5–6. Closure per pick; drop parents whose closure fails perm/risk
    kept: list[str] = []
    for aid in greedy_ids:
        if _closure_passes_hard_filters(aid, req, registry):
            kept.append(aid)

    # Closure BFS over surviving greedy picks (full registry)
    result = dependency_closure(kept, registry)

    # 7. Mandatory control plane: permission only (skip risk), like include_control_plane
    for mid in mandatory_control_plane:
        if mid in result:
            continue
        agent = registry.get(mid)
        if agent is None:
            continue
        if permission_eligible(agent, req):
            result.append(mid)

    # 8. Already unique via dependency_closure + append checks
    return result
