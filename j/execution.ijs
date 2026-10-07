
NB. =============================================================================
NB. Synthetic David — WorkItem / AgentResult sparse execution (PURE J)
NB. Locale: david. Selected agents only — no swarm fan-out.
NB. Python ../execution stays smoke harness only.
NB. =============================================================================

cocurrent 'david'

NB. WorkItem (boxed fields):
NB.   0 request_id  1 work_id  2 agent_id  3 task
NB.   4 evidence_ids  5 required_outputs  6 permissions  7 deadline  8 risk_policy
NB.
NB. AgentResult (boxed fields):
NB.   0 agent_id  1 status  2 conclusions  3 evidence_refs  4 provenance_root

NB. Peel scalar boxes only (never open a row of mixed boxes)
openscalar =: 3 : 0
  v =. y
  while. (32 = 3!:0 v) *. (0 = # $ v) do. v =. > v end.
  v
)

field =: 4 : 'openscalar x { y'

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

NB. x = request ; y = selected agent_id list
build_work_items =: 4 : 0
  aids =. uniqseq y
  rid =. 0 field x
  task =. 1 field x
  eids =. boxopen 2 field x
  outs =. boxopen 3 field x
  perms =. boxopen 4 field x
  rpol =. 5 field x
  dl =. 6 field x
  wis =. 0 $ a:
  i =. 0
  while. i < # aids do.
    aid =. openscalar i { aids
    wid =. rid , ':' , aid
    wi =. (<rid) ; (<wid) ; (<aid) ; (<task) ; (<eids) ; (<outs) ; (<perms) ; (<dl) ; (<rpol)
    wis =. wis , < wi
    i =. i + 1
  end.
  wis
)

make_stub =: 3 : 0
  aid =. 2 field y
  rid =. 0 field y
  eids =. boxopen 4 field y
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

smoke =: 3 : 0
  selected =. 'LegacyCobol' ; 'Database' ; 'ReverseEngineering' ; 'Provenance' ; 'Risk' ; 'Response'
  req =. 'req-cobol-1' ; 'Explain COBOL balance vs Java' ; (<'e1') ; ('business_rules' ; 'equivalence_result') ; ('read_source' ; 'read_copybooks') ; 'escalate_on_high' ; 'none'
  wis =. req build_work_items selected
  wids =. 2 fields wis
  assert. selected -: wids
  assert. -. (< 'Quant') e. wids
  rs =. req dispatch_selected selected
  rids =. 0 fields rs
  assert. selected -: rids
  assert. -. (< 'Quant') e. rids
  assert. *./ (<'ok') = 1 fields rs
  assert. 0 = # (req dispatch_selected (0 $ a:))
  eids =. boxopen 4 field openscalar 0 { wis
  assert. (< 'e1') e. eids
  'ok' ; (# wis) ; (# rs)
)
