<!--
  Copyright (C) 2026 Synthetic David contributors
  SPDX-License-Identifier: AGPL-3.0-only
-->

# Synthetic David (SMoA)

Sparse Mixture of Agents router: embeddings propose candidates; symbols
decide eligibility. Product stack is **J + PostgreSQL/pgvector + Prolog**.
Python under `evidence/`, `execution/`, and `router/*.py` is a **smoke
harness only** — not the product.

Embeddings answer “who looks capable?” Executable Prolog
(`router/symbolic_rules.pl`) plus the J eligibility caller
(`j/eligibility.ijs`) answer “who is permitted and sufficient?” Similarity
is never the authority.

## Product vs harness

| Path | Role |
|------|------|
| `j/` | Product — scorer, execution, evidence, eligibility |
| `sql/` | Product — AGENT / EVIDENCE indexes + hybrid retrieve |
| `registry/` | Product — AgentDescriptor schema + seeds |
| `router/symbolic_rules.pl`, `registry_facts.pl` | Product — SWI-Prolog eligibility |
| `docs/` | Contracts |
| `logs/` | Measured smoke outputs |
| `evidence/*.py`, `execution/*.py`, `router/*.py` | Harness only |

## Quick start

Requires `jconsole` and (for Prolog) SWI-Prolog.

```bash
jconsole j/run_evidence_smoke.ijs
jconsole j/run_execution_smoke.ijs
swipl -q -s router/symbolic_rules.pl -g smoke_cobol -t halt
./scripts/check_prolog_registry_sync.sh
cd j && jconsole run_eligibility_smoke.ijs
```

Optional live PostgreSQL 17 + pgvector smokes:
`scripts/load_agent_registry.py`, `scripts/agent_ann_smoke.py`,
`scripts/load_evidence_seed.py`, `scripts/evidence_hybrid_smoke.py`.

## Measured smokes

Facts from `logs/` only:

| Smoke | Result | Log |
|-------|--------|-----|
| J evidence | `ok`; top ids include copybook / cobol_src / db2 | `logs/j_evidence_smoke.log` |
| J execution | `ok` ; `6` ; `6` | `logs/j_execution_smoke.log` |
| Prolog `smoke_cobol` | selected legacyCobol…response; `OK` | `logs/prolog_smoke_cobol.log` |
| Prolog↔registry sync | `OK` (10 agents) | `logs/prolog_registry_sync.log` |
| J→Prolog eligibility | Quant absent; `eligibility_smoke: OK` | `logs/prolog_eligibility_smoke.log` |
| Live AGENT ANN | LegacyCobol top; Quant not preferred | `logs/agent_ann_smoke.log` |
| Live EVIDENCE hybrid | copybook/cobol/db2 above Quant; `pass=True` | `logs/evidence_hybrid_smoke.log` |

## Layout

```
david/
  LICENSE
  README.md
  j/              product J + smoke drivers
  sql/            PostgreSQL/pgvector schema + queries
  registry/       descriptors + seeds
  router/         Prolog rules/facts; Python harness
  scripts/        harness sync + live DB smokes
  evidence/       Python smoke harness
  execution/      Python smoke harness
  docs/           contracts + images
  logs/           measured outputs
```

## Demo

![David demos](docs/images/david-demos.png)

## Out of scope

- Growing Python trees as the product surface
- Inventing PostgreSQL timings without a real local run
- Foundry F1 audit/linker/seals (see [foundry-j](https://github.com/AHMADALIPARR/foundry-j) for math cores only)

## License

Copyright © 2026 Synthetic David contributors. **AGPL-3.0-only** — see
[`LICENSE`](LICENSE).
