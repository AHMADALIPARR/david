"""Smoke: only selected agents receive WorkItems and run."""

from __future__ import annotations

import unittest

from execution.models import Evidence, EvidenceBundle
from execution.dispatcher import (
    ExecutionRequest,
    build_work_items,
    dispatch,
    stub_handler,
)


SELECTED = [
    "LegacyCobol",
    "Database",
    "ReverseEngineering",
    "Provenance",
    "Risk",
    "Response",
]


class TestSparseDispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = EvidenceBundle(
            sources=(
                Evidence(
                    evidence_id="e1",
                    source_id="s1",
                    source_type="cobol_source",
                    document_id="pay.cbl",
                    location="lines:100-200",
                    content_hash="abc",
                    content="COMPUTE BALANCE ...",
                ),
            ),
        )
        self.req = ExecutionRequest(
            request_id="req-cobol-1",
            task=(
                "Explain how this COBOL payment program calculates "
                "the account balance and determine whether its Java "
                "replacement preserves the behavior."
            ),
            evidence_bundle=self.bundle,
            required_outputs=("business_rules", "equivalence_result"),
            permissions=frozenset(
                {"read_source", "read_copybooks", "read_schema", "read_evidence"}
            ),
            risk_policy="escalate_on_high",
        )
        self.handlers = {aid: stub_handler(aid) for aid in SELECTED}
        # Quant must never run even if a handler exists.
        self.handlers["Quant"] = stub_handler("Quant")

    def test_work_items_only_for_selected(self) -> None:
        items = build_work_items(SELECTED, self.req)
        self.assertEqual([i.agent_id for i in items], SELECTED)
        self.assertTrue(all(i.request_id == "req-cobol-1" for i in items))
        self.assertNotIn("Quant", [i.agent_id for i in items])

    def test_dispatch_invokes_only_selected(self) -> None:
        invoked: list[str] = []

        def wrap(aid: str):
            inner = stub_handler(aid)

            def _h(item):
                invoked.append(aid)
                return inner(item)

            return _h

        handlers = {aid: wrap(aid) for aid in self.handlers}
        results = dispatch(SELECTED, self.req, handlers)
        self.assertEqual([r.agent_id for r in results], SELECTED)
        self.assertEqual(invoked, SELECTED)
        self.assertNotIn("Quant", invoked)
        self.assertTrue(all(r.status == "ok" for r in results))

    def test_empty_selection_runs_nobody(self) -> None:
        results = dispatch([], self.req, self.handlers)
        self.assertEqual(results, [])

    def test_evidence_bundle_not_bare_text(self) -> None:
        items = build_work_items(["LegacyCobol"], self.req)
        src = items[0].evidence_bundle.sources[0]
        self.assertEqual(src.evidence_id, "e1")
        self.assertEqual(src.content_hash, "abc")
        self.assertIsNotNone(src.source_id)


if __name__ == "__main__":
    unittest.main()
