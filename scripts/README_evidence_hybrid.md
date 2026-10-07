# Live EVIDENCE-index Postgres hybrid smoke

Product indexes / retrieve: `sql/001_agent_and_evidence_indexes.sql`,
`sql/002_evidence_hybrid_retrieve.sql`, fixtures in `sql/003_evidence_seed_cobol.sql`
(embedding left NULL in 003 — loader fills vectors).

Harness (Python, not product):
- `load_evidence_seed.py` — same fixture IDs as 003 → `evidence`, deterministic hashed
  bag-of-tokens → `vector(1536)` via `embed` / `fmt_vector` from `load_agent_registry.py`
- `evidence_hybrid_smoke.py` — COBOL balance hybrid query (dense + lexical + authority;
  `min_authority=0.5`; `require_parent=false` — junk dropped by authority floor)

Done criteria: `ev_copybook_01` / `ev_cobol_src_01` / `ev_db2_schema_01` beat Quant;
`ev_junk_low_auth` dropped at `min_authority=0.5`.

Measured log: `logs/evidence_hybrid_smoke.log`
