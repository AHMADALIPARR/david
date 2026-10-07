# Live AGENT-index Postgres smoke

Product indexes: `sql/001_agent_and_evidence_indexes.sql` (pgvector).

Harness (Python, not product):
- `load_agent_registry.py` — `registry/seed_agents.yaml` → `agent_registry`, deterministic hashed bag-of-tokens → `vector(1536)`
- `agent_ann_smoke.py` — COBOL balance query ANN top-K (`<=>` cosine)

Done criteria: LegacyCobol in top-K; Quant not preferred before symbolic filter.

Measured log: `logs/agent_ann_smoke.log`
