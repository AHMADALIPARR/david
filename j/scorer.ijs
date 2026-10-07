NB. =============================================================================
NB. Synthetic David — deterministic agent scorer (PURE J)
NB. Port of router/scorer.py scoring shape. Locale: david
NB. =============================================================================

cocurrent 'david'

WPOS =: 1.0 1.2 1.0 0.8 0.6
WNEG =: 0.9 1.5 0.7

RISKLABEL =: 'low';'medium';'high';'critical'
RISKPEN   =: 0.0 0.15 0.35 0.55

riskix =: 3 : 0
  i =. RISKLABEL i. <y
  if. i = #RISKLABEL do. 1 else. i end.
)

jaccard =: 4 : 0
  a =. ~. boxopen x
  b =. ~. boxopen y
  if. (0 = #a) *. (0 = #b) do. 1.0 return. end.
  if. (0 = #a) +. (0 = #b) do. 0.0 return. end.
  (# a -. a -. b) % (# ~. a , b)
)

NB. Fetch and open field i from boxed row y
field =: 4 : '> (x { y)'

NB. x = req: caps ; inputs ; perms ; <max_risk
NB. y = agent row (9 boxed fields)
score_agent =: 4 : 0
  rcaps =. 0 field x
  ain   =. 1 field x
  gperm =. 2 field x
  maxr  =. 3 field x
  caps  =. 1 field y
  ins   =. 2 field y
  perms =. 3 field y
  rcls  =. 4 field y
  deps  =. 5 field y
  hist  =. 0 >. 1 <. (6 field y)
  cp    =. 7 field y
  sem   =. 8 field y
  cap   =. caps jaccard rcaps
  inp   =. ins  jaccard ain
  dep   =. (0 = # boxopen deps) { 0.5 1.0
  miss  =. 0 < # (boxopen perms) -. boxopen gperm
  rix   =. riskix rcls
  rpen  =. rix { RISKPEN
  if. rix > riskix maxr do. rpen =. rpen + 1 end.
  unnec =. -. ((cap > 0) +. (cp ~: 0))
  (+/ WPOS * sem,cap,inp,hist,dep) - +/ WNEG * rpen,miss,unnec
)

smoke =: 3 : 0
  NB. ; boxes each item once — do not pre-box scalars
  req =. ('cobol';'business_rule_extraction') ; ('source_code';'copybooks') ; ('read_source';'read_copybooks') ; 'high'
  legacy =. 'LegacyCobol' ; ('cobol';'business_rule_extraction') ; (<'source_code') ; (<'read_source') ; 'high' ; ('Database';'Provenance') ; 0.5 ; 0 ; 0.92
  quant  =. 'Quant' ; ('pricing';'monte_carlo') ; (<'source_code') ; (<'read_source') ; 'medium' ; (0$a:) ; 0.5 ; 0 ; 0.1
  sl =. req score_agent legacy
  sq =. req score_agent quant
  assert. sl > sq
  'ok' ; sl ; sq
)
