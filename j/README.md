# David core (J)

Stack lock: **J + PostgreSQL/pgvector + Prolog**.

| Path | Role |
|------|------|
| `scorer.ijs` | Deterministic score shape (ported from Python harness) |
| `eligibility.ijs` | **Product** — J → SWI-Prolog eligibility (candidates + request → minimum agent set) |
| `run_eligibility_smoke.ijs` | Product smoke for `eligibility.ijs` (ANN fixture + Quant negative) |
| `symbolic_call.ijs` | Thin delegate → `run_eligibility_smoke.ijs` |
| `execution.ijs` | WorkItem → AgentResult; selected agents only |
| `run_execution_smoke.ijs` | Smoke for `execution.ijs` |
| `evidence.ijs` | Hybrid evidence retrieve (product; seed + `ev_retrieve` / `ev_smoke`) |
| `run_evidence_smoke.ijs` | Smoke for `evidence.ijs` |
| `fixtures/ann_topk.txt` | Fixture candidate ids (ANN top-K shape + Quant negative) |
| `../sql/001_agent_and_evidence_indexes.sql` | AGENT / EVIDENCE indexes |
| `../sql/002_evidence_hybrid_retrieve.sql` | Product hybrid retrieve against `evidence` |
| `../router/symbolic_rules.pl` | Product Prolog eligibility rules |
| `../router/registry_facts.pl` | Generated agent facts from `registry/seed_agents.yaml` |

Python under `../router`, `../execution`, `../evidence` is smoke only — not the product.

Foundry J lives separately at `/workspace/foundry-j`.
