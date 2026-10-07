# David contracts

## WorkItem (agent input)

```
request_id, work_id, agent_id
task, evidence_bundle, required_outputs
permissions, deadline, risk_policy
```

## AgentResult (agent output)

```
agent_id
facts[], conclusions[], assumptions[], uncertainty[]
evidence_refs[], transformations[]
risk_signals[], provenance_root, status
```

## Evidence / EvidenceBundle

See architecture §5. Every chunk carries source, hash, authority, and parent links —
agents never receive bare text without provenance.

## Execution wiring

`execution/` builds one WorkItem per selected `agent_id` and dispatches only that set.
Unselected agents (e.g. Quant on a COBOL migration query) never receive work.

## Symbolic hard filters (`router/symbolic.py`)

Predicates (not score penalties). An agent is eligible only if all three hold:

- **capability_eligible** — `capabilities ∩ required_capabilities ≠ ∅`, or `control_plane`
- **permission_eligible** — `permissions ⊆ granted_permissions`
- **risk_eligible** — `risk_class` does not exceed `max_risk_class` (`low < medium < high < critical`)

`apply_symbolic_filters` returns the agents that pass all three.
`minimum_agent_set` scores via `scorer.score_agent`, takes top-K, hard-filters, greedy-covers required capabilities, closes dependencies, then appends mandatory control-plane agents (`Risk`, `Response`). Pure dependency agents waive capability_eligible; after closure every agent must still pass permission + risk (else the parent needing a failing dep is dropped). Mandatory control plane skips the risk gate but still requires permission (same as scorer `include_control_plane`).
