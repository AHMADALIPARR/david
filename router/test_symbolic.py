"""Smoke tests for symbolic hard filters + minimum_agent_set."""

from __future__ import annotations

import unittest

from scorer import AgentDescriptor, RequestContext
from symbolic import (
    apply_symbolic_filters,
    capability_eligible,
    minimum_agent_set,
    permission_eligible,
    risk_eligible,
)


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


class SymbolicTests(unittest.TestCase):
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

    def test_cobol_query_minimum_set(self):
        selected = minimum_agent_set(self.candidates, self.req, self.registry)
        self.assertIn("LegacyCobol", selected)
        self.assertIn("Database", selected)
        self.assertIn("Provenance", selected)
        self.assertNotIn("Quant", selected)
        self.assertIn("Risk", selected)
        self.assertIn("Response", selected)

    def test_quant_never_selected_for_cobol(self):
        selected = minimum_agent_set(self.candidates, self.req, self.registry)
        self.assertNotIn("Quant", selected)
        self.assertFalse(capability_eligible(self.registry["Quant"], self.req))

    def test_permission_filter_drops_ungranted(self):
        sneaky = _agent(
            "SneakyWrite",
            ["cobol"],
            perms=("read_source", "write_prod"),
        )
        req = RequestContext(
            required_capabilities=frozenset({"cobol"}),
            available_inputs=frozenset({"source_code"}),
            granted_permissions=frozenset({"read_source"}),
            max_risk_class="high",
            semantic_scores={"SneakyWrite": 0.99},
        )
        self.assertFalse(permission_eligible(sneaky, req))
        filtered = apply_symbolic_filters([sneaky], req)
        self.assertEqual(filtered, [])
        selected = minimum_agent_set([sneaky], req, {"SneakyWrite": sneaky})
        self.assertNotIn("SneakyWrite", selected)

    def test_risk_filter_drops_critical_when_max_medium(self):
        critical = _agent("HotPath", ["cobol"], risk="critical")
        req = RequestContext(
            required_capabilities=frozenset({"cobol"}),
            available_inputs=frozenset({"source_code"}),
            granted_permissions=frozenset({"read_source"}),
            max_risk_class="medium",
            semantic_scores={"HotPath": 0.99, "Risk": 0.2, "Response": 0.2},
        )
        self.assertFalse(risk_eligible(critical, req))
        filtered = apply_symbolic_filters([critical], req)
        self.assertEqual(filtered, [])

        # Mandatory control plane still included despite Risk being critical
        # (risk gate skipped for mandatory CP; permission still required).
        registry = {
            "HotPath": critical,
            "Risk": self.registry["Risk"],
            "Response": self.registry["Response"],
        }
        selected = minimum_agent_set(
            list(registry.values()), req, registry
        )
        self.assertNotIn("HotPath", selected)
        self.assertIn("Risk", selected)
        self.assertIn("Response", selected)


if __name__ == "__main__":
    unittest.main()
