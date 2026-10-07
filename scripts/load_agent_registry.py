#!/usr/bin/env python3
"""Harness: seed_agents.yaml → agent_registry with deterministic 1536-d vectors."""
from __future__ import annotations

import hashlib
import math
import re
import sys
from pathlib import Path

import yaml

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "registry" / "seed_agents.yaml"
DIM = 1536

TOKEN_RE = re.compile(r"[a-z0-9_]+")


def embed_text_of(agent: dict) -> str:
    parts = [
        agent["agent_id"],
        agent.get("domain", ""),
        " ".join(agent.get("capabilities") or []),
        " ".join(agent.get("languages") or []),
        " ".join(agent.get("input_types") or []),
        " ".join(agent.get("output_types") or []),
        " ".join(agent.get("dependencies") or []),
        agent.get("risk_class", ""),
    ]
    return " ".join(p for p in parts if p).lower()


def embed(text: str, dim: int = DIM) -> list[float]:
    """Deterministic hashed bag-of-tokens → L2-normalized vector(dim)."""
    vec = [0.0] * dim
    toks = TOKEN_RE.findall(text.lower())
    if not toks:
        vec[0] = 1.0
        return vec
    for tok in toks:
        h = hashlib.sha256(tok.encode()).digest()
        # two lanes per token for a bit of spread
        for off in (0, 8):
            idx = int.from_bytes(h[off : off + 4], "little") % dim
            sign = 1.0 if h[off + 4] & 1 else -1.0
            vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def fmt_vector(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]"


def main() -> int:
    agents = yaml.safe_load(SEED.read_text())
    dsn = sys.argv[1] if len(sys.argv) > 1 else "dbname=david user=david host=127.0.0.1"
    if psycopg2 is None:
        print("psycopg2 missing", file=sys.stderr)
        return 2

    rows = []
    for a in agents:
        et = embed_text_of(a)
        emb = embed(et)
        rows.append(
            (
                a["agent_id"],
                a["domain"],
                a.get("capabilities") or [],
                a.get("languages") or [],
                a.get("input_types") or [],
                a.get("output_types") or [],
                a.get("required_evidence") or [],
                a.get("permissions") or [],
                a["risk_class"],
                a.get("dependencies") or [],
                a["execution_endpoint"],
                bool(a.get("control_plane", False)),
                et,
                fmt_vector(emb),
                float(a.get("historical_success", 0.5)),
            )
        )

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE agent_registry")
        sql = """
        INSERT INTO agent_registry (
          agent_id, domain, capabilities, languages, input_types, output_types,
          required_evidence, permissions, risk_class, dependencies,
          execution_endpoint, control_plane, embed_text, embedding, historical_success
        ) VALUES %s
        """
        template = (
            "(%s,%s,%s::text[],%s::text[],%s::text[],%s::text[],"
            "%s::text[],%s::text[],%s,%s::text[],%s,%s,%s,%s::vector,%s)"
        )
        execute_values(cur, sql, rows, template=template)
        cur.execute("SELECT count(*) FROM agent_registry")
        n = cur.fetchone()[0]
    conn.close()
    print(f"loaded_agents={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
