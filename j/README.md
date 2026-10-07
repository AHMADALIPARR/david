# David core (J)

Stack lock: **J + PostgreSQL/pgvector**.

| Path | Role |
|------|------|
| `scorer.ijs` | Deterministic score shape (ported from Python harness) |
| `symbolic_call.ijs` | Thin J spawn of Spec Prolog smoke (`../router/symbolic_rules.pl`) |
| `execution.ijs` | WorkItem → AgentResult; selected agents only |
| `run_execution_smoke.ijs` | Smoke for `execution.ijs` |
| `evidence.ijs` | Hybrid evidence retrieve (product; seed + `ev_retrieve` / `ev_smoke`) |
| `run_evidence_smoke.ijs` | Smoke for `evidence.ijs` |
| `../sql/001_agent_and_evidence_indexes.sql` | AGENT / EVIDENCE indexes |
| `../sql/002_evidence_hybrid_retrieve.sql` | Product hybrid retrieve against `evidence` |

Python under `../router`, `../execution`, `../evidence` is smoke only — not the product.

Foundry J lives separately at `/workspace/foundry-j`.
