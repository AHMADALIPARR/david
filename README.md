# Synthetic David (SMoA)

Sparse Mixture of Agents router: embeddings propose candidates; symbols decide eligibility. Product stack is **J + PostgreSQL/pgvector + Prolog**. Python under `evidence/`, `execution/`, and `router/*.py` is a **smoke harness only** — not the product.

## Idea

- Embeddings answer “who looks capable?”
- Executable Prolog (`router/symbolic_rules.pl`) plus the J scorer answer “who is permitted and sufficient?”
- Similarity is never the authority; only the minimum justified agent set executes.

## Product vs harness

| Layer | Role |
|-------|------|
| `j/` | **Product** — scorer, execution, evidence retrieve (`scorer.ijs`, `execution.ijs`, `evidence.ijs`) |
| `sql/` | **Product** — AGENT / EVIDENCE indexes and hybrid retrieve SQL (for PostgreSQL + pgvector) |
| `registry/` | **Product** — `AgentDescriptor` schema + seed descriptors |
| `router/symbolic_rules.pl` | **Product** — symbolic eligibility (SWI-Prolog) |
| `docs/` | Contracts (WorkItem / AgentResult / Evidence) |
| `logs/` | Measured smoke outputs |
| `evidence/*.py`, `execution/*.py`, `router/*.py` | **Harness only** — do not grow as the product |

This repository does **not** claim a live Postgres/pgvector instance was exercised in CI here. SQL is shipped as product schema/query text; smoke results below are from J and Prolog harnesses.

## Layout

```text
j/                 J product (scorer, execution, evidence, smokes)
sql/               PostgreSQL/pgvector indexes + hybrid retrieve
registry/          agent descriptor schema + seeds
router/
  symbolic_rules.pl   product Prolog eligibility
  *.py                Python smoke harness
evidence/          Python smoke harness (J evidence.ijs is product)
execution/         Python smoke harness (J execution.ijs is product)
docs/              contracts + screenshot placeholders
logs/              measured smoke logs
LICENSE            AGPL-3.0-only
```

## Measured smoke results

Facts only (no invented Postgres timings or live DB claims):

**Evidence smoke (J)** — `ok`; top ids  
`ev_copybook_01`, `ev_cobol_src_01`, `ev_db2_schema_01`, `ev_lexical_lift_01`, `ev_quant_pricing_01`  
(quant is present in the top set but not #1).  
Log: `logs/j_evidence_smoke.log`

**Execution smoke (J)** — `ok` ; `6` ; `6`  
Log: `logs/j_execution_smoke.log`

**Prolog smoke (`smoke_cobol`)** —  
`selected:[legacyCobol,database,reverseEngineering,provenance,risk,response]`  
`smoke_cobol: OK`  
Log: `logs/prolog_smoke_cobol.log`

## How to run smokes

Requires J `jconsole` and (for Prolog) SWI-Prolog.

```bash
# J evidence
jconsole j/run_evidence_smoke.ijs

# J execution
jconsole j/run_execution_smoke.ijs

# Prolog COBOL eligibility smoke (see router/symbolic_rules.pl)
swipl -q -s router/symbolic_rules.pl -g smoke_cobol -t halt
```

Exact invocation may match local `j/` README helpers. Python harness tests are optional and are not the product path.

## Demo screenshots

Screenshots land under `docs/images/`:

![David demos](docs/images/david-demos.png)

![David evidence smoke](docs/images/david-evidence.png)

![David execution smoke](docs/images/david-execution.png)

![David Prolog smoke](docs/images/david-prolog.png)

*(Primary capture is `david-demos.png`; the evidence/execution/prolog names are aliases of the same shot for now.)*

## License

**AGPL-3.0-only** — see [`LICENSE`](LICENSE).

## Out of scope

- Alapeno hardware and Foundry F1 audit/linker/seals (see sibling [foundry-j](https://github.com/AHMADALIPARR/foundry-j) for pure-J math cores only)
- Growing the Python trees as the product surface
- Claiming live PostgreSQL/pgvector query results in this README
