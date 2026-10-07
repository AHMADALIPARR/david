<!--
  Copyright (C) 2026 Synthetic David contributors
  SPDX-License-Identifier: AGPL-3.0-only
-->

# Synthetic David

**A sparse mixture-of-agents router in which embeddings propose and symbols decide — built on J, PostgreSQL with pgvector, and SWI-Prolog, with a separate Python smoke harness that is not the product.**

---

## Abstract

Synthetic David routes a work request to the smallest set of specialist agents that is *capable*, *permitted*, and *sufficient* to handle it, and hands each selected agent only evidence that carries provenance. It addresses a specific failure of similarity-only routing: an agent whose description happens to sit close to a query in embedding space is not thereby authorized to act on it, nor is it guaranteed to cover what the request needs.

The design separates two questions and gives each to the tool suited to it.

- **Who looks capable?** Answered by nearest-neighbour search over agent and evidence embeddings in PostgreSQL with pgvector, and by a deterministic J scorer. These produce *candidates* and *rankings*.
- **Who is permitted and sufficient?** Answered by executable Prolog rules over a registry of agent descriptors: hard eligibility predicates, a greedy capability cover, dependency closure, and mandatory control-plane agents. This produces the *decision*.

Similarity never overrides the rules. A candidate that the embeddings rank highly but the rules reject does not receive work. The running example throughout the repository is a COBOL modernization request — explain how a payment program computes an account balance and whether a Java replacement preserves the behaviour — with a deliberately irrelevant *Quant* agent (option pricing, Monte Carlo) present as a negative control.

This README describes the routing model, the product stack, the harness and why it is kept separate, how to run every smoke, and what the logs on disk show.

---

## 1. Product versus harness

The repository contains two kinds of code, and the distinction is the first thing to understand about it.

| Path | Kind | Role |
|---|---|---|
| `j/` | product | scorer, eligibility caller, evidence retrieval, sparse execution, smoke drivers |
| `sql/` | product | agent and evidence tables, vector and text indexes, hybrid retrieval query, seed fixtures |
| `registry/` | product | agent descriptor schema and seed registry |
| `router/symbolic_rules.pl` | product | executable eligibility rules (SWI-Prolog) |
| `router/registry_facts.pl` | product (generated) | Prolog facts generated from `registry/seed_agents.yaml` |
| `docs/` | contracts | WorkItem, AgentResult, EvidenceBundle, execution wiring |
| `logs/` | evidence | outputs of real smoke runs |
| `router/*.py`, `evidence/*.py`, `execution/*.py` | harness | Python reference implementations and unit tests used during design |
| `scripts/` | harness | registry-to-Prolog sync, Prolog handoff, live database loaders and smokes |

The **product** is J plus PostgreSQL/pgvector plus Prolog. The Python code was used to prototype the scoring and filtering logic and is retained as a smoke harness: it loads fixtures into PostgreSQL, embeds text for the live smokes, and checks that the registry and the generated Prolog facts agree. It is not on the decision path, it is not meant to grow, and where its outputs differ from the product's (see §8.5) the product is authoritative.

---

## 2. The routing model

### 2.1 Agent descriptors

Every routable agent is a record in `registry/seed_agents.yaml`, validated by `registry/agent_descriptor.schema.json` and mirrored in the `agent_registry` table. The fields that matter for routing are:

| Field | Meaning |
|---|---|
| `agent_id` | stable identifier, e.g. `LegacyCobol` |
| `capabilities` | what the agent can do, e.g. `cobol`, `business_rule_extraction` |
| `input_types`, `required_evidence` | what it consumes |
| `permissions` | what it must be granted to run, e.g. `read_source` |
| `risk_class` | `low` < `medium` < `high` < `critical` |
| `dependencies` | other agents it needs, e.g. `LegacyCobol` needs `Database`, `ReverseEngineering`, `Provenance` |
| `control_plane` | whether it is a governance agent (`Risk`, `Audit`, `Response`) |

The seed registry has ten agents: `LegacyCobol`, `Database`, `ReverseEngineering`, `Modernization`, `MigrationValidation`, `Provenance`, `Risk`, `Audit`, `Response`, and the negative control `Quant`. Agents are *routable descriptors*, not permanently running processes.

### 2.2 A request

A request carries a set of required capabilities $R$, a set of granted permissions $G$, a maximum risk class $m$, and optionally a set of candidate agents $A_{\mathrm{ann}}$ proposed by nearest-neighbour search. For the COBOL example:

- $R$ = { `cobol`, `business_rule_extraction` }
- $G$ = read source, copybooks, schema, evidence, all results, conclusions; write provenance
- $m = \texttt{high}$

### 2.3 Hard eligibility predicates

For an agent $a$ with capabilities $\mathrm{cap}(a)$, permissions $\mathrm{perm}(a)$, and risk class $\rho(a)$, and a request $r = (R, G, m)$, define

$$
\mathrm{CapOK}(a, r) \iff \mathrm{cp}(a) \ \lor\ \mathrm{cap}(a) \cap R \neq \emptyset ,
$$

$$
\mathrm{PermOK}(a, r) \iff \mathrm{perm}(a) \subseteq G ,
$$

$$
\mathrm{RiskOK}(a, r) \iff \mathrm{rank}(\rho(a)) \le \mathrm{rank}(m),
$$

where $\mathrm{cp}(a)$ is the control-plane flag and $\mathrm{rank}$ maps `low`, `medium`, `high`, `critical` to $0, 1, 2, 3$. An agent is **eligible** when all three hold. These are predicates, not score penalties: no amount of similarity compensates for a missing permission.

Two relaxed forms are used for agents that enter the selection by other routes:

$$
\mathrm{DepOK}(a, r) \iff \mathrm{PermOK}(a, r) \land \mathrm{RiskOK}(a, r), \qquad
\mathrm{MandOK}(a, r) \iff \mathrm{cp}(a) \land \mathrm{PermOK}(a, r).
$$

A dependency need not share a required capability (a database agent is needed by a COBOL agent without itself knowing COBOL), but it must still be permitted and within risk. A mandatory control-plane agent is exempt from the risk ceiling — the `Risk` agent is itself classed `critical` — but not from permissions.

### 2.4 Minimum agent set

The selection runs in four stages, implemented as `minimum_agent_set/2` in `router/symbolic_rules.pl`:

1. **Core candidates.** $C = \lbrace a : \text{eligible}(a, r),\ \lnot \mathrm{cp}(a),\ \mathrm{cap}(a) \cap R \ne \emptyset,\ a \in A_{\mathrm{ann}} \rbrace$. The last condition applies only when ANN candidates were supplied; otherwise the whole registry is considered.
2. **Greedy cover.** Starting from the uncovered set $U = R$, repeatedly pick the candidate covering the most uncovered capabilities (ties broken by a deterministic sort), remove what it covers, and stop when $U$ is empty or no candidate covers anything. Call the result the seed $S_0$.
3. **Dependency closure.** Take the transitive closure of $S_0$ under `depends/2` by breadth-first expansion, keep the agents that satisfy $\mathrm{DepOK}$, then drop any agent whose own dependencies did not survive. This is what prevents a parent from being dispatched without something it needs.
4. **Mandatory control plane.** Append `Risk` and `Response` if they satisfy $\mathrm{MandOK}$, and remove duplicates.

Greedy cover is the classical approximation for minimum set cover; with two required capabilities and one agent covering both, as in the example, it is exact.

### 2.5 Worked example

With the COBOL request and the ANN candidates in `j/fixtures/ann_topk.txt` (`LegacyCobol`, `ReverseEngineering`, `MigrationValidation`, `Modernization`, `Response`, `Quant`):

- `LegacyCobol` covers both required capabilities, needs only the permissions `read_source` and `read_copybooks`, both in $G$, and has risk `high`, equal to the ceiling. It is the greedy seed.
- `Quant` shares no capability with $R$, and its permission `read_market_data` is not granted. It fails two predicates and is never a candidate, despite appearing in the ANN list.
- Closure adds `Database`, `ReverseEngineering`, and `Provenance`, the dependencies of `LegacyCobol`. All three pass $\mathrm{DepOK}$. `Database` and `Provenance` were not in the ANN list; they enter through the dependency rule, which is the point of having one.
- `Risk` and `Response` are appended as mandatory control plane. `Audit` is a control-plane agent but not a mandatory one, and it is not selected.

The selection is `legacyCobol, database, reverseEngineering, provenance, risk, response` — six agents out of ten, with Quant absent. That is precisely what the logs record (§8).

### 2.6 Deterministic scoring

Ranking within candidates uses a deterministic linear score, ported from the Python prototype to `j/scorer.ijs` with the same weights:

$$
\mathrm{score}(a) = 1.0\,s_{\mathrm{sem}} + 1.2\,J_{\mathrm{cap}} + 1.0\,J_{\mathrm{in}} + 0.8\,h + 0.6\,d \;-\; \left( 0.9\,\pi_{\mathrm{risk}} + 1.5\,\pi_{\mathrm{perm}} + 0.7\,\pi_{\mathrm{unn}} \right).
$$

Here $s_{\mathrm{sem}}$ is the semantic similarity supplied by retrieval; $J_{\mathrm{cap}}$ and $J_{\mathrm{in}}$ are Jaccard similarities between the agent's capabilities and $R$ and between its input types and the available inputs,

$$
J(A, B) = \frac{\lvert A \cap B \rvert}{\lvert A \cup B \rvert} ;
$$

$h \in [0, 1]$ is clipped historical success; $d$ is $1$ for an agent without dependencies and $0.5$ otherwise; $\pi_{\mathrm{risk}}$ is $0$, $0.15$, $0.35$, or $0.55$ by risk class, plus $1$ if the class exceeds the ceiling; $\pi_{\mathrm{perm}}$ is $1$ if any permission is missing; and $\pi_{\mathrm{unn}}$ is $1$ for a non-control-plane agent with no required capability. The scorer's built-in smoke asserts that `LegacyCobol` outscores `Quant` on the COBOL request. Scores order candidates; they do not decide eligibility.

---

## 3. Evidence retrieval

Agents never receive bare text. Evidence lives in its own table and vector space, separate from the agent index, because the two answer different questions: *who should work* and *what should they read*.

### 3.1 Schema

`sql/001_agent_and_evidence_indexes.sql` creates the `vector` and `pg_trgm` extensions and two tables:

- `agent_registry` — descriptor fields, an `embed_text`, a `vector(1536)` embedding with an HNSW cosine index, and a GIN index on capabilities.
- `evidence` — `evidence_id`, `source_id`, `source_type`, document and location, `content`, `content_hash`, a `vector(1536)` embedding with an HNSW cosine index, a generated English `tsvector` with a GIN index, `source_authority`, and `parent_evidence` links.

### 3.2 Hybrid score

`sql/002_evidence_hybrid_retrieve.sql` ranks evidence by a sum of three signals minus an optional penalty:

$$
\mathrm{score}(e) = \underbrace{\left(1 - d_{\cos}(\mathbf{v}_e, \mathbf{v}_q)\right)}_{\text{dense}} + \underbrace{\mathrm{lex}(e, q)}_{\text{lexical}} + \underbrace{\alpha_e}_{\text{authority}} - \underbrace{\pi_e}_{\text{parent}} ,
$$

where $d_{\cos}$ is pgvector's cosine distance (`<=>`), $\mathrm{lex}(e, q)$ is PostgreSQL's `ts_rank_cd` of the passage against `plainto_tsquery('english', q)`, $\alpha_e$ is the source authority, and $\pi_e = 1$ only when the caller requires a parent link and the row has none. Rows below a minimum authority are filtered out; an optional `source_type` filter and an optional parent requirement act as hard provenance gates. There is deliberately no floor on the dense term, so a passage with weak embedding similarity but a strong lexical match can still rank. Ties break on `evidence_id` for stability.

### 3.3 The J retrieval path

`j/evidence.ijs` implements the same scoring shape over the six-row seed corpus that `sql/003_evidence_seed_cobol.sql` loads into PostgreSQL. Because no encoder is shipped, the J path uses stand-ins: an eight-axis query embedding over the terms `cobol`, `balance`, `payment`, `schema`, `pricing`, `vol`, `greek`, `junk`, and a lexical score equal to the fraction of query tokens present in the passage,

$$
\mathrm{lex}(q, c) = \frac{\lvert \mathrm{tok}(q) \cap \mathrm{tok}(c) \rvert}{\lvert \mathrm{tok}(q) \rvert} .
$$

The corpus contains a copybook, a COBOL procedure, a DB2 schema, a glossary entry engineered to have weak dense but strong lexical similarity, a quant pricing report as negative control, and a low-authority web scrape with no parent link as junk.

### 3.4 Evidence bundles

`j/execution.ijs` treats an evidence row as acceptable only if its `evidence_id`, `source_id`, and `content_hash` are all non-empty. A bundle is acceptable only if it is non-empty and every row is acceptable. A row consisting of text alone is rejected.

---

## 4. Sparse execution

Execution is sparse by construction: one WorkItem per selected agent, and none for anyone else.

- **WorkItem**: `request_id`, `work_id`, `agent_id`, `task`, `evidence_bundle`, `required_outputs`, `permissions`, `deadline`, `risk_policy`.
- **AgentResult**: `agent_id`, `facts`, `conclusions`, `assumptions`, `uncertainty`, `evidence_refs`, `transformations`, `risk_signals`, `provenance_root`, `status`.

`build_work_items` asserts that the bundle is acceptable, deduplicates the selected agent ids while preserving order, and builds one WorkItem per id with `work_id = request_id:agent_id`. `dispatch_selected` maps WorkItems to AgentResults; in this repository the agents are stubs that return status `ok`, a placeholder conclusion, the evidence ids from the bundle, and a provenance root. The contracts are written out in [`docs/contracts.md`](docs/contracts.md).

---

## 5. The J ↔ Prolog bridge

The product path from J to the rules is short and explicit, and involves no Python:

1. `j/eligibility.ijs` writes a temporary Prolog file of request facts — `required_capability/2`, `granted_permission/2`, `max_risk_class/2`, and one `ann_candidate/2` per proposed agent. Registry identifiers are mapped to Prolog atoms by lower-casing the first letter (`LegacyCobol` becomes `legacyCobol`).
2. It runs `swipl` on `router/symbolic_rules.pl`, consulting the request file and calling `run_eligibility/1`.
3. It parses the single output line `selected:[…]` into a list of atoms.

For the execution smoke, `scripts/prolog_selected_handoff.sh` runs the rules' built-in COBOL request and writes the selected set to `logs/selected_cobol.txt`, one atom per line, which `load_selected` in `j/execution.ijs` reads.

The rules include `router/registry_facts.pl`, which is generated from the YAML registry by `scripts/gen_registry_facts.py`. `scripts/check_prolog_registry_sync.sh` regenerates the facts into a temporary file, fails if they differ from the committed file, checks that every registry agent has an `agent_id/2` fact, and checks that the Quant negative is present. That keeps the decision rules and the registry from drifting apart silently.

---

## 6. Repository layout

```
david/
  LICENSE                       GNU AGPL v3 (AGPL-3.0-only)
  README.md                     this document
  j/
    scorer.ijs                  deterministic score (locale david)
    eligibility.ijs             J -> swipl eligibility (product entry)
    evidence.ijs                hybrid evidence retrieval over seed corpus
    execution.ijs               WorkItem / AgentResult, bundle checks
    run_smoke.ijs               scorer smoke
    run_eligibility_smoke.ijs   eligibility smoke (ANN fixture + Quant)
    run_evidence_smoke.ijs      evidence smoke
    run_execution_smoke.ijs     handoff + execution smoke
    symbolic_call.ijs           delegate to the eligibility smoke
    fixtures/ann_topk.txt       ANN-style candidate list
  sql/
    001_agent_and_evidence_indexes.sql
    002_evidence_hybrid_retrieve.sql
    003_evidence_seed_cobol.sql
  registry/
    agent_descriptor.schema.json
    seed_agents.yaml
  router/
    symbolic_rules.pl           eligibility rules (product)
    registry_facts.pl           generated facts (product)
    scorer.py, symbolic.py, test_*.py      harness
  evidence/, execution/         Python harness and tests
  scripts/                      sync, handoff, live DB loaders and smokes
  docs/
    contracts.md
    images/                     screenshots of the smokes
  logs/                         measured outputs
```

---

## 7. Running the smokes

### 7.1 Requirements

| Tool | Needed for |
|---|---|
| J 9.x (`jconsole`) | all J smokes |
| SWI-Prolog (`swipl` on `PATH`) | Prolog smoke, eligibility smoke, execution handoff |
| Python 3 | registry sync check and live database smokes (harness) |
| PostgreSQL with `pgvector` and `pg_trgm`, plus `psycopg2` | optional live smokes |

### 7.2 Offline product smokes

Run from the repository root unless noted:

```bash
# Scorer
cd j && jconsole run_smoke.ijs && cd ..

# Prolog rules on the built-in COBOL request
swipl -q -s router/symbolic_rules.pl -g smoke_cobol -t halt

# Registry <-> generated Prolog facts
./scripts/check_prolog_registry_sync.sh

# J -> Prolog eligibility with ANN fixture and Quant negative
cd j && jconsole run_eligibility_smoke.ijs && cd ..

# Evidence retrieval and sparse execution
cd j && jconsole run_evidence_smoke.ijs && cd ..
cd j && jconsole run_execution_smoke.ijs && cd ..
```

The J drivers resolve paths relative to `j/` (for example `../router/symbolic_rules.pl`), so run them from that directory. Each driver calls `exit` so that `jconsole` returns.

### 7.3 Optional live PostgreSQL smokes

The default connection string in the scripts is `dbname=david user=david host=127.0.0.1`; pass another as the first argument.

```bash
psql -d david -f sql/001_agent_and_evidence_indexes.sql
python3 scripts/load_agent_registry.py      # registry -> agent_registry
python3 scripts/agent_ann_smoke.py          # ANN top-K over agents
python3 scripts/load_evidence_seed.py       # seed fixtures -> evidence
python3 scripts/evidence_hybrid_smoke.py    # hybrid retrieval over evidence
```

The loaders embed text with a deterministic hashed bag of tokens: each token is hashed with SHA-256, two hash lanes select coordinates and signs in a 1536-dimensional vector, and the result is $\ell_2$-normalized. This is a reproducible stand-in for a learned encoder, sufficient to exercise the indexes, the query, and the ranking logic. It is not a semantic model, and the similarity values in the live logs should be read as properties of that stand-in.

---

## 8. Measured results

Every value below is copied from a file in `logs/`. No timings are reported because none were measured.

### 8.1 Prolog rules — `logs/prolog_smoke_cobol.log`

```
selected:[legacyCobol,database,reverseEngineering,provenance,risk,response]
smoke_cobol: OK
```

The smoke asserts the presence of LegacyCobol, Database, Provenance, Risk, and Response and the absence of Quant.

### 8.2 Registry sync — `logs/prolog_registry_sync.log`

`sync ok: 10 agents; Quant present as negative` followed by `prolog_registry_sync: OK`.

### 8.3 J → Prolog eligibility — `logs/prolog_eligibility_smoke.log`

| Stage | Agents |
|---|---|
| ANN candidates passed in | LegacyCobol, ReverseEngineering, MigrationValidation, Modernization, Response, Quant |
| selected by the rules | legacyCobol, database, reverseEngineering, provenance, risk, response |

Result line: `eligibility_smoke: OK`. Quant was proposed and rejected; Database and Provenance were not proposed and were added by dependency closure.

### 8.4 J evidence and execution

| Smoke | Log | Output |
|---|---|---|
| evidence | `logs/j_evidence_smoke.log` | `ok`, then ids in rank order: `ev_copybook_01`, `ev_cobol_src_01`, `ev_db2_schema_01`, `ev_lexical_lift_01`, `ev_quant_pricing_01` |
| execution | `logs/j_execution_smoke.log` | `ok`, `6`, `6`, `3` |

The evidence smoke asserts that the quant report is not first and not in the top three, that at least one legacy source is returned, that the junk row is dropped at minimum authority $0.5$ and present at $0$, and that an empty query returns nothing. The execution smoke's four fields are: status, number of selected agents read from the Prolog handoff, number of AgentResults produced, and number of evidence references on the first result. Along the way it asserts that a bundle with a missing content hash and an empty bundle are both rejected, that WorkItems and AgentResults correspond one-to-one with the selected set, that dispatching an empty selection produces nothing, and that Quant receives no WorkItem.

### 8.5 Live PostgreSQL smokes

**Agent ANN** (`logs/agent_ann_smoke.log`), top five by cosine similarity for the COBOL query:

| Rank | Agent | Domain | Risk | Similarity |
|---|---|---|---|---|
| 1 | LegacyCobol | legacy_mainframe | high | 0.406562 |
| 2 | ReverseEngineering | legacy_mainframe | medium | 0.309016 |
| 3 | MigrationValidation | migration | high | 0.160817 |
| 4 | Modernization | migration | high | 0.154508 |
| 5 | Response | control_plane | medium | 0.000000 |

`legacy_in_topk=True`, `quant_not_preferred=True`, `pass=True`.

**Evidence hybrid** (`logs/evidence_hybrid_smoke.log`), lexical query `payment balance account`, top five, minimum authority $0.5$, no parent requirement:

| Rank | Evidence | Source type | Score | Dense | Lexical | Authority |
|---|---|---|---|---|---|---|
| 1 | ev_cobol_src_01 | cobol_source | 1.589825 | 0.583714 | 0.106111 | 0.90 |
| 2 | ev_copybook_01 | copybook | 1.323832 | 0.359546 | 0.014286 | 0.95 |
| 3 | ev_lexical_lift_01 | glossary | 1.207805 | 0.482805 | 0.025000 | 0.70 |
| 4 | ev_db2_schema_01 | db2_schema | 1.104701 | 0.243590 | 0.011111 | 0.85 |
| 5 | ev_quant_pricing_01 | quant_report | 1.030079 | 0.230079 | 0.000000 | 0.80 |

Each score is the sum of its three components, as the query defines. `junk_exists=True`, `junk_dropped=True`, `legacy_in_topk=True`, `quant_not_preferred=True`, `pass=True`. The ordering differs from the offline J smoke (which ranks the copybook first) because the two use different embedding and lexical stand-ins; both place the legacy sources above the quant report.

**Python harness** (`logs/router_smoke.log`, 2026-10-07 06:14 PDT). The Python prototype's `minimum_agent_set` selected LegacyCobol, Database, Provenance, Risk, and Response, with Quant absent. It did not include ReverseEngineering, which the current registry lists as a dependency of LegacyCobol and which the Prolog product does select. The harness log is kept as a record; the product result is the one in §8.1 and §8.3.

---

## 9. Design rationale

**Why symbols decide.** Eligibility is a policy question with crisp answers: an agent either holds a permission or it does not, and either covers a requirement or it does not. Encoding that in Prolog makes the policy executable, inspectable, and testable on its own, and makes "why was this agent selected?" answerable by reading rules rather than by interpreting a similarity score.

**Why separate agent and evidence indexes.** Agent descriptions and source passages have different vocabularies and different failure modes. Mixing them in one vector space would let a well-described agent outrank relevant evidence or the reverse. Two tables, two indexes, two queries.

**Why provenance is a hard gate.** A conclusion is only as good as the evidence it can cite. Requiring an id, a source, and a content hash on every row means every AgentResult can point to exactly what it read.

**Why J.** The routing core is a small set of set operations, weighted sums, and record manipulations. J expresses them compactly, runs without a heavy runtime, and calls out to `swipl` with a single system call.

**Why the Python harness is frozen.** It was the fastest way to prototype and to drive the database. Letting it grow would create a second, competing implementation of the policy. It stays as a harness; new logic goes into J, SQL, or Prolog.

---

## 10. Relationship to other repositories

| Repository | Relationship |
|---|---|
| [foundry-j](https://github.com/AHMADALIPARR/foundry-j) | Pure-J recreation of the Foundry F1 math cores. Shares the J toolchain; no code dependency. |
| [hcalc](https://github.com/AHMADALIPARR/hcalc) | Nested contraction recurrence with Alloy, Lean, and J renderings. No relationship beyond J and licensing. |
| [sedona-k](https://github.com/AHMADALIPARR/sedona-k) | Layer-1 Riemann-gas thermodynamics in ngn/k. Unrelated. |

---

## 11. Out of scope

- Real agent implementations. The dispatched agents are stubs that echo their evidence references.
- A learned embedding model. Live smokes use a deterministic hashed stand-in; the J path uses an eight-axis stand-in.
- Latency, throughput, or index-performance figures. None have been measured, and none are reported.
- Growing the Python code into a product surface.
- Foundry F1 audit, linker, or seal machinery.
- Continuous-integration workflows.

---

## 12. Screenshots

![David demos](docs/images/david-demos.png)

Further captures of the individual smokes are in `docs/images/` (`david-prolog.png`, `david-evidence.png`, `david-execution.png`).

---

## 13. License

Copyright © 2026 Synthetic David contributors.

Distributed under the GNU Affero General Public License, **version 3 only** — see [`LICENSE`](LICENSE). SPDX identifier: `AGPL-3.0-only`.
