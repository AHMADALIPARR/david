
NB. =============================================================================
NB. Synthetic David — WorkItem / AgentResult sparse execution (PURE J)
NB. Locale: david. Selected agents only — no swarm fan-out.
NB. Product path: Prolog selected-set → dispatch_selected; EvidenceBundle only.
NB. Python ../execution stays smoke harness only.
NB. =============================================================================

cocurrent 'david'

NB. Evidence row (boxed fields):
NB.   0 evidence_id  1 source_id  2 source_type  3 content_hash  4 authority
NB.
NB. WorkItem (boxed fields):
NB.   0 request_id  1 work_id  2 agent_id  3 task
NB.   4 evidence_rows  5 required_outputs  6 permissions  7 deadline  8 risk_policy
NB.
NB. AgentResult (boxed fields):
NB.   0 agent_id  1 status  2 conclusions  3 evidence_refs  4 provenance_root

openscalar =: 3 : 0
  v =. y
  while. (32 = 3!:0 v) *. (0 = # $ v) do. v =. > v end.
  v
)

field =: 4 : 'openscalar x { y'

NB. Non-empty character / open content
nonempty =: 3 : 0
  v =. openscalar y
  if. 32 = 3!:0 v do. 0 return. end.
  0 < # v
)

NB. One evidence row is ok iff evidence_id, source_id, content_hash are non-empty.
NB. Bare text alone is never enough.
evidence_row_ok =: 3 : 0
  r =. y
  if. 3 > # r do. 0 return. end.
  (nonempty 0 { r) *. (nonempty 1 { r) *. (nonempty 3 { r)
)

NB. Bundle = list of boxed evidence rows; empty bundle is not ok for dispatch.
bundle_ok =: 3 : 0
  rows =. y
  if. 0 = # rows do. 0 return. end.
  i =. 0
  ok =. 1
  while. i < # rows do.
    ok =. ok *. evidence_row_ok openscalar i { rows
    i =. i + 1
  end.
  ok
)

uniqseq =: 3 : 0
  if. 0 = # y do. 0 $ a: return. end.
  ys =. boxopen y
  out =. 0 $ a:
  i =. 0
  while. i < # ys do.
    v =. openscalar i { ys
    if. -. (< v) e. out do. out =. out , < v end.
    i =. i + 1
  end.
  out
)

fields =: 4 : 0
  rows =. y
  i =. 0
  out =. 0 $ a:
  while. i < # rows do.
    row =. openscalar i { rows
    out =. out , < x field row
    i =. i + 1
  end.
  out
)

NB. Load selected agent ids from a text file (one id per line).
NB. Product handoff from Prolog / Spec J→swipl writer.
load_selected =: 3 : 0
  if. 0 = # (1!:0 < y) do. 0 $ a: return. end.
  raw =. 1!:1 < y
  lines =. <;._2 raw , LF
  out =. 0 $ a:
  i =. 0
  while. i < # lines do.
    s =. openscalar i { lines
    NB. drop CR if present (Windows handoff)
    if. (2 = 3!:0 s) *. (0 < # s) do.
      if. 13 = {: s do. s =. }: s end.
    end.
    if. (2 = 3!:0 s) *. (0 < # s) do. out =. out , < s end.
    i =. i + 1
  end.
  uniqseq out
)

NB. Evidence ids from validated bundle rows
bundle_ids =: 3 : 0
  rows =. y
  out =. 0 $ a:
  i =. 0
  while. i < # rows do.
    r =. openscalar i { rows
    out =. out , < 0 field r
    i =. i + 1
  end.
  out
)

NB. x = request: request_id ; task ; evidence_bundle ; required_outputs ; permissions ; risk_policy ; deadline
NB. y = selected agent_id list (from Prolog)
NB. Fails assert if bundle is not EvidenceBundle-ok (no bare text).
build_work_items =: 4 : 0
  bundle =. 2 field x
  NB. field peels the outer box; bundle is a list of evidence rows
  if. (32 = 3!:0 bundle) *. (0 = # $ bundle) do. bundle =. , < openscalar bundle end.
  assert. bundle_ok bundle
  aids =. uniqseq y
  rid =. 0 field x
  task =. 1 field x
  outs =. boxopen 3 field x
  perms =. boxopen 4 field x
  rpol =. 5 field x
  dl =. 6 field x
  wis =. 0 $ a:
  i =. 0
  while. i < # aids do.
    aid =. openscalar i { aids
    wid =. rid , ':' , aid
    wi =. (<rid) ; (<wid) ; (<aid) ; (<task) ; (<bundle) ; (<outs) ; (<perms) ; (<dl) ; (<rpol)
    wis =. wis , < wi
    i =. i + 1
  end.
  wis
)

make_stub =: 3 : 0
  aid =. 2 field y
  rid =. 0 field y
  brows =. boxopen 4 field y
  eids =. bundle_ids brows
  (<aid) ; (<'ok') ; (< 'stub:' , aid) ; (<eids) ; (< 'prov:' , rid , ':' , aid)
)

NB. x = request ; y = selected agent ids → AgentResult list (selected only)
dispatch_selected =: 4 : 0
  wis =. x build_work_items y
  rs =. 0 $ a:
  i =. 0
  while. i < # wis do.
    rs =. rs , < make_stub openscalar i { wis
    i =. i + 1
  end.
  rs
)

NB. Fixture EvidenceBundle rows (ids/hashes/authority — not bare text alone)
good_bundle =: 3 : 0
  e1 =. (<'ev_cobol_src_01') ; (<'src_cobol') ; (<'cobol_source') ; (<'hash_cobol') ; (<'0.9')
  e2 =. (<'ev_copybook_01') ; (<'src_copy') ; (<'copybook') ; (<'hash_copy') ; (<'0.85')
  e3 =. (<'ev_db2_schema_01') ; (<'src_db2') ; (<'db_schema') ; (<'hash_db2') ; (<'0.8')
  (<e1) , (<e2) , (<e3)
)

bad_bundle_no_hash =: 3 : 0
  e1 =. (<'ev_bare') ; (<'src_x') ; (<'text') ; (<'') ; (<'0.9')
  , < e1
)

smoke =: 3 : 0
  NB. Selected set from Prolog handoff file (written by run_execution_smoke.ijs)
  selected =. load_selected '../logs/selected_cobol.txt'
  assert. 0 < # selected
  assert. (< 'legacyCobol') e. selected
  assert. -. (< 'quant') e. selected
  assert. -. (< 'Quant') e. selected

  assert. bundle_ok good_bundle 0
  assert. -. bundle_ok bad_bundle_no_hash 0
  assert. -. bundle_ok (0 $ a:)

  req =. 'req-cobol-1' ; 'Explain COBOL balance vs Java' ; (< good_bundle 0) ; ('business_rules' ; 'equivalence_result') ; ('read_source' ; 'read_copybooks') ; 'escalate_on_high' ; 'none'
  wis =. req build_work_items selected
  wids =. 2 fields wis
  assert. selected -: wids
  assert. -. (< 'quant') e. wids
  rs =. req dispatch_selected selected
  rids =. 0 fields rs
  assert. selected -: rids
  assert. *./ (<'ok') = 1 fields rs
  assert. 0 = # (req dispatch_selected (0 $ a:))

  NB. Evidence refs on results are bundle ids, not bare text
  refs0 =. boxopen 3 field openscalar 0 { rs
  assert. (< 'ev_cobol_src_01') e. refs0

  'ok' ; (# selected) ; (# rs) ; (# refs0)
)
