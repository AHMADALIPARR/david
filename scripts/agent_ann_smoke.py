#!/usr/bin/env python3
"""Harness: embed COBOL balance query, ANN top-K against agent_registry."""
from __future__ import annotations

import math
import sys
from pathlib import Path

# reuse embed from loader
sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_agent_registry import embed, fmt_vector

import psycopg2

QUERY = (
    "Explain how this COBOL payment program calculates the account balance "
    "and determine whether its Java replacement preserves the behavior. "
    "cobol copybook business_rule_extraction control_flow data_flow "
    "legacy_mainframe modernization_analysis"
)
TOP_K = 5


def main() -> int:
    dsn = sys.argv[1] if len(sys.argv) > 1 else "dbname=david user=david host=127.0.0.1"
    qvec = fmt_vector(embed(QUERY))
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT agent_id, domain, risk_class,
                   1 - (embedding <=> %s::vector) AS cosine_sim
            FROM agent_registry
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, qvec, TOP_K),
        )
        rows = cur.fetchall()
    conn.close()

    print(f"query={QUERY[:80]}...")
    print(f"top_k={TOP_K}")
    for i, (aid, domain, risk, sim) in enumerate(rows, 1):
        print(f"{i}\t{aid}\t{domain}\t{risk}\tsim={sim:.6f}")

    ids = [r[0] for r in rows]
    ok_legacy = "LegacyCobol" in ids
    # Quant should not outrank LegacyCobol (prefer: Legacy ahead of Quant if both present)
    if "Quant" in ids and "LegacyCobol" in ids:
        ok_order = ids.index("LegacyCobol") < ids.index("Quant")
    else:
        ok_order = "Quant" not in ids[:1]  # Quant not the preferred top hit

    print(f"legacy_in_topk={ok_legacy}")
    print(f"quant_not_preferred={ok_order}")
    print(f"pass={ok_legacy and ok_order}")
    return 0 if (ok_legacy and ok_order) else 1


if __name__ == "__main__":
    raise SystemExit(main())
