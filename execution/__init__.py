"""Sparse agent execution: WorkItem in, AgentResult out, selected set only."""

from .dispatcher import (
    ExecutionRequest,
    build_work_items,
    dispatch,
    stub_handler,
)
from .models import AgentResult, Evidence, EvidenceBundle, WorkItem

__all__ = [
    "AgentResult",
    "Evidence",
    "EvidenceBundle",
    "ExecutionRequest",
    "WorkItem",
    "build_work_items",
    "dispatch",
    "stub_handler",
]
