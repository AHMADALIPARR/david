NB. Thin J caller for Spec Prolog eligibility (not a second filter).
NB. Requires swipl on PATH. Spawn: /home/box/j/j9.7/bin/jconsole symbolic_call.ijs

PL=: 'swipl -q -s ../router/symbolic_rules.pl -g smoke_cobol -t halt'
echo 2!:0 PL
exit ''
