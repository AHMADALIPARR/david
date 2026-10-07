NB. =============================================================================
NB. Synthetic David — hybrid evidence retrieve (PURE J)
NB. Product path against sql/001 evidence indexes; Python evidence/ stays harness.
NB. Locale: david. Verbs prefixed ev_ to avoid clobbering scorer/execution names.
NB. Smoke embeddings dim 8; production SQL uses vector(1536).
NB. =============================================================================

cocurrent 'david'

NB. --- field accessors (row is boxed list) ------------------------------------
ev_field =: 4 : '> (x { y)'

NB. Open one level if boxed
ev_unbox1 =: 3 : 'if. 32 = 3!:0 y do. > y else. y end.'

NB. --- lowercase + alphanumeric tokens len>1 (lexical stand-in for tsv) -------
EV_AZ =: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
EV_az =: 'abcdefghijklmnopqrstuvwxyz'
EV_alnum =: EV_az , '0123456789'

ev_lc1 =: 3 : 0
  i =. EV_AZ i. y
  if. i < #EV_AZ do. i { EV_az else. y end.
)

ev_lc =: 3 : 'ev_lc1"0 y'

ev_tokens =: 3 : 0
  if. 0 = #y do. 0 $ a: return. end.
  s =. ev_lc , y
  ok =. s e. EV_alnum
  s =. ok } (' ' #~ #s) ,: s
  parts =. <;._1 ' ' , s
  parts =. parts #~ 1 < #&> parts
  ~. parts
)

NB. lexical overlap = |q ∩ c| / |q|  (0 if empty query tokens)
ev_lexical =: 4 : 0
  q =. ev_tokens x
  if. 0 = #q do. 0.0 return. end.
  c =. ev_tokens y
  if. 0 = #c do. 0.0 return. end.
  (# q -. q -. c) % #q
)

NB. cosine similarity of two numeric lists
ev_cosine =: 4 : 0
  a =. , x
  b =. , y
  if. (#a) ~: #b do. 0.0 return. end.
  if. (0 = #a) +. (0 = #b) do. 0.0 return. end.
  na =. %: +/ *: a
  nb =. %: +/ *: b
  if. (0 = na) +. (0 = nb) do. 0.0 return. end.
  (+/ a * b) % (na * nb)
)

NB. Axes for dim-8 smoke query embed (prod = vector(1536) via encoder)
NB.   [cobol, balance, payment, schema, pricing, vol, greek, junk]
EV_AXES =: 'cobol';'balance';'payment';'schema';'pricing';'vol';'greek';'junk'

ev_qembed =: 3 : 0
  toks =. ev_tokens y
  NB. synonym: volatility → vol
  if. (<'volatility') e. toks do. toks =. toks , <'vol' end.
  v =. 0 #~ #EV_AXES
  i =. 0
  while. i < #EV_AXES do.
    if. (i { EV_AXES) e. toks do. v =. 1 i} v end.
    i =. i + 1
  end.
  NB. fallback canned COBOL qvec when axis hits empty but query non-blank
  if. (0 = +/ v) *. (0 < #y) do.
    v =. 0.93 0.91 0.88 0.25 0.05 0 0 0
  end.
  v
)

NB. --- seed corpus (mirrors sql/003 + Python harness columns) -----------------
NB. row: id ; source_id ; source_type ; document_id ; location ;
NB.      content ; authority ; parent_boxed ; embedding (dim 8 smoke)

ev_mk =: 3 : 0
  NB. y already a 9-field boxed row
  y
)

EV_CORPUS =: 0 $ a:

NB. ev_copybook_01
EV_CORPUS =: EV_CORPUS , < ('ev_copybook_01' ; 'src_copybook_acct' ; 'copybook' ; 'ACCTREC.cpy' ; '01-ACCOUNT-BALANCE' ; '01 ACCOUNT-RECORD. 05 ACCOUNT-BALANCE PIC S9(9)V99. 05 PAYMENT-AMOUNT PIC S9(7)V99. 05 LAST-PAYMENT-DATE PIC X(8).' ; 0.95 ; (<'ev_provenance_root') ; 0.95 0.90 0.85 0.20 0.05 0 0 0)

NB. ev_cobol_src_01
EV_CORPUS =: EV_CORPUS , < ('ev_cobol_src_01' ; 'src_cobol_pay' ; 'cobol_source' ; 'PAYROLL.cbl' ; 'PROCEDURE DIVISION / CALC-BALANCE' ; 'COMPUTE ACCOUNT-BALANCE = ACCOUNT-BALANCE - PAYMENT-AMOUNT. IF ACCOUNT-BALANCE < ZERO THEN PERFORM OVERDRAFT-CHECK. MOVE PAYMENT-AMOUNT TO WS-LAST-PAYMENT.' ; 0.90 ; (<'ev_provenance_root') ; 0.92 0.88 0.90 0.15 0.05 0 0 0)

NB. ev_db2_schema_01
EV_CORPUS =: EV_CORPUS , < ('ev_db2_schema_01' ; 'src_db2_acct' ; 'db2_schema' ; 'ACCT.DDL' ; 'TABLE ACCOUNT_BALANCES' ; 'CREATE TABLE ACCOUNT_BALANCES (ACCT_ID CHAR(12), BALANCE DECIMAL(11,2), LAST_PAYMENT DECIMAL(9,2), UPDATED_TS TIMESTAMP).' ; 0.85 ; (<'ev_provenance_root') ; 0.70 0.80 0.55 0.95 0.05 0 0 0)

NB. ev_quant_pricing_01
EV_CORPUS =: EV_CORPUS , < ('ev_quant_pricing_01' ; 'src_quant_report' ; 'quant_report' ; 'PRICING_Q3.pdf' ; 'section:monte_carlo' ; 'Monte Carlo pricing of exotic options. Implied volatility surface and greek sensitivities. No COBOL or account balance fields.' ; 0.80 ; (<'ev_provenance_root') ; 0.05 0.05 0.05 0.05 0.95 0.90 0.85 0.10)

NB. ev_lexical_lift_01 — weak dense, strong lexical (no dense floor)
EV_CORPUS =: EV_CORPUS , < ('ev_lexical_lift_01' ; 'src_glossary' ; 'glossary' ; 'LEGACY-GLOSSARY.txt' ; 'entry:PAYMENT-BALANCE' ; 'cobol payment balance glossary entry: PAYMENT and BALANCE fields on ACCOUNT records in legacy batch.' ; 0.70 ; (<'ev_provenance_root') ; 0.10 0.15 0.10 0.05 0.40 0.35 0.30 0.20)

NB. ev_junk_low_auth — authority ~0.1, no parents
EV_CORPUS =: EV_CORPUS , < ('ev_junk_low_auth' ; 'src_web_scrape' ; 'web_scrape' ; 'random-blog.html' ; 'body' ; 'Someone said COBOL payment balance might work like a spreadsheet. Unverified forum post.' ; 0.10 ; (0 $ a:) ; 0.60 0.55 0.50 0.10 0.10 0 0 0.9)

NB. --- score one row ----------------------------------------------------------
NB. score = dense + lexical + authority - parent_penalty
NB. (no dense floor — lexical can lift weak dense)
NB. x = query ; qvec ; require_parent   y = corpus row
ev_score_row =: 4 : 0
  q =. 0 ev_field x
  qv =. 1 ev_field x
  reqp =. 2 ev_field x
  row =. y
  emb =. 8 ev_field row
  content =. 5 ev_field row
  auth =. 6 ev_field row
  parents =. boxopen 7 ev_field row
  dense =. qv ev_cosine emb
  lex =. q ev_lexical content
  pen =. 0.0
  if. reqp *. (0 = # parents) do. pen =. 1.0 end.
  dense + lex + auth - pen
)

NB. --- retrieve ---------------------------------------------------------------
NB. y = query ; min_authority ; top_k  [; require_parent]
NB. returns boxed list of (evidence_id ; score) sorted score DESC, id ASC
ev_retrieve =: 3 : 0
  args =. y
  q =. 0 ev_field args
  min_a =. 1 ev_field args
  top_k =. 2 ev_field args
  reqp =. 0
  if. 3 < # args do. reqp =. 3 ev_field args end.
  NB. empty / blank query → empty result
  if. 0 = # q do. 0 $ a: return. end.
  if. 0 = # ev_tokens q do. 0 $ a: return. end.
  qv =. ev_qembed q
  ctx =. q ; qv ; reqp
  ids =. 0 $ a:
  scores =. 0 $ 0.0
  i =. 0
  while. i < # EV_CORPUS do.
    row =. ev_unbox1 i { EV_CORPUS
    auth =. 6 ev_field row
    parents =. boxopen 7 ev_field row
    if. auth >: min_a do.
      if. (-. reqp) +. (0 < # parents) do.
        sc =. ctx ev_score_row row
        ids =. ids , < 0 ev_field row
        scores =. scores , sc
      end.
    end.
    i =. i + 1
  end.
  if. 0 = # ids do. 0 $ a: return. end.
  NB. stable: id asc then score desc → ORDER BY score DESC, evidence_id
  ix =. /: ids
  ix =. ix \: ix { scores
  if. top_k < # ix do. ix =. top_k {. ix end.
  out =. 0 $ a:
  j =. 0
  while. j < # ix do.
    k =. j { ix
    out =. out , < ((k { ids) ; k { scores)
    j =. j + 1
  end.
  out
)

NB. peel nested boxes to open string
ev_openstr =: 3 : 0
  v =. y
  while. 32 = 3!:0 v do. v =. > v end.
  v
)

NB. ids only from retrieve result (single-boxed strings)
ev_ids =: 3 : 0
  rs =. y
  out =. 0 $ a:
  i =. 0
  while. i < # rs do.
    out =. out , < ev_openstr 0 ev_field ev_unbox1 i { rs
    i =. i + 1
  end.
  out
)

NB. --- smoke ------------------------------------------------------------------
ev_smoke =: 3 : 0
  q =. 'cobol account payment balance CALC-BALANCE'
  NB. 1) COBOL-ish ranks copybook/cobol/db2 above quant; quant not #1
  r1 =. ev_retrieve q ; 0.5 ; 5 ; 1
  ids1 =. ev_ids r1
  assert. 0 < # ids1
  assert. -. (< 'ev_quant_pricing_01') -: 0 { ids1
  legacy =. 'ev_copybook_01' ; 'ev_cobol_src_01' ; 'ev_db2_schema_01'
  assert. 0 < # (ids1 -. ids1 -. legacy)
  top3 =. 3 <. # ids1
  top3 =. top3 {. ids1
  assert. -. (< 'ev_quant_pricing_01') e. top3
  NB. 2) min_authority 0.5 drops junk
  r2 =. ev_retrieve q ; 0.5 ; 10 ; 0
  ids2 =. ev_ids r2
  assert. -. (< 'ev_junk_low_auth') e. ids2
  r2open =. ev_retrieve q ; 0.0 ; 10 ; 0
  ids2o =. ev_ids r2open
  assert. (< 'ev_junk_low_auth') e. ids2o
  NB. 3) empty query → empty result
  r3 =. ev_retrieve '' ; 0.0 ; 10
  assert. 0 = # r3
  'ok' ; ids1
)
