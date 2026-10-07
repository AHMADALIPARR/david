NB. SPDX-License-Identifier: AGPL-3.0-only
NB. J → Prolog eligibility product smoke.
NB. Fixtures: caps cobol+business_rule_extraction; ANN-style candidates + Quant negative.
NB. Assert: LegacyCobol, Database, Provenance (deps), Risk, Response; Quant absent.
NB. MUST call exit so jconsole does not hang.

(0!:0) <'eligibility.ijs'
cocurrent 'david'

elig_smoke=: 3 : 0
  caps=. 'cobol';'business_rule_extraction'
  perms=. 'read_source';'read_copybooks';'read_schema';'read_evidence';'write_provenance';'read_all_results';'read_conclusions'
  maxr=. 'high'
  cands=. load_cand_fixture 'fixtures/ann_topk.txt'
  echo 'candidates:'; cands
  sel=. elig_query (<caps),(<perms),(<maxr),(<cands)
  echo 'selected:'; sel
  need=. 'legacyCobol';'database';'provenance';'risk';'response'
  missing=. need -. sel
  extra_quant=. (<'quant') e. sel
  if. (0 = #missing) *. -. extra_quant do.
    echo 'eligibility_smoke: OK'
    0
  else.
    if. #missing do. echo 'FAIL missing:'; missing end.
    if. extra_quant do. echo 'FAIL Quant present' end.
    echo 'eligibility_smoke: FAIL'
    1
  end.
)

rc=. elig_smoke 0
exit rc
