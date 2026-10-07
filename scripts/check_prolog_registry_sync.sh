#!/usr/bin/env bash
# Harness: regenerate registry_facts.pl and fail if dirty vs committed tree.
# Exit 0 iff generated facts match router/registry_facts.pl on disk.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GEN="$ROOT/scripts/gen_registry_facts.py"
TARGET="$ROOT/router/registry_facts.pl"
TMP="$(mktemp "${TMPDIR:-/tmp}/registry_facts.XXXXXX.pl")"
trap 'rm -f "$TMP"' EXIT

python3 "$GEN" "$TMP"
if ! cmp -s "$TMP" "$TARGET"; then
  echo "FAIL: router/registry_facts.pl out of sync with registry/seed_agents.yaml" >&2
  echo "Diff (generated vs on-disk):" >&2
  diff -u "$TARGET" "$TMP" >&2 || true
  echo "Re-run: python3 scripts/gen_registry_facts.py" >&2
  exit 1
fi

# Also require that symbolic_rules.pl includes the generated facts.
if ! grep -q "include('registry_facts.pl')" "$ROOT/router/symbolic_rules.pl" \
   && ! grep -q 'include("registry_facts.pl")' "$ROOT/router/symbolic_rules.pl" \
   && ! grep -q "include(registry_facts)" "$ROOT/router/symbolic_rules.pl"; then
  echo "FAIL: symbolic_rules.pl must include registry_facts.pl" >&2
  exit 1
fi

# Spot-check: every agent_id from YAML appears as agent_id/2 in facts.
python3 - <<'PY' "$ROOT"
import re, sys
from pathlib import Path
root = Path(sys.argv[1])
yaml_text = (root / "registry" / "seed_agents.yaml").read_text()
facts = (root / "router" / "registry_facts.pl").read_text()
ids = re.findall(r"(?m)^-\s*agent_id:\s*(\S+)", yaml_text)
missing = [i for i in ids if f"agent_id('{i}'" not in facts]
if missing:
    print("FAIL: missing agent_id/2 for:", ", ".join(missing), file=sys.stderr)
    sys.exit(1)
if "agent(quant)." not in facts:
    print("FAIL: Quant negative agent missing", file=sys.stderr)
    sys.exit(1)
print(f"sync ok: {len(ids)} agents; Quant present as negative")
PY

echo "prolog_registry_sync: OK"
