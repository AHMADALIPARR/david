#!/bin/sh
# Materialize Prolog smoke_cobol selection as one agent_id per line.
set -e
cd "$(dirname "$0")/.."
swipl -q -s router/symbolic_rules.pl -g smoke_cobol -t halt > logs/prolog_selected_cobol.raw
sed -n 's/^selected:\[\(.*\)\]/\1/p' logs/prolog_selected_cobol.raw   | tr ',' '\n' | tr -d ' []' | sed '/^$/d' > logs/selected_cobol.txt
