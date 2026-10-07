"""Smoke tests for deterministic sparse selection."""

from __future__ import annotations

import unittest

from scorer import AgentDescriptor, RequestContext, score_agent, select_minimum_set


def _agent(aid, caps, deps=(), control=False, risk="medium", perms=(), inputs=()):
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


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
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
        self.candidates = list(self.registry.values())
        self.req = RequestContext(
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

    def test_cobol_query_excludes_quant(self):
        selected = select_minimum_set(self.candidates, self.req, self.registry)
        self.assertIn("LegacyCobol", selected)
        self.assertIn("Database", selected)
        self.assertIn("Provenance", selected)
        self.assertNotIn("Quant", selected)
        self.assertIn("Risk", selected)
        self.assertIn("Response", selected)

    def test_score_orders_legacy_above_quant(self):
        legacy = score_agent(self.registry["LegacyCobol"], self.req)
        quant = score_agent(self.registry["Quant"], self.req)
        self.assertGreater(legacy, quant)


if __name__ == "__main__":
    unittest.main()
