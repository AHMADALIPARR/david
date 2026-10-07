#!/usr/bin/env python3
"""Harness: embed COBOL balance query, hybrid retrieve against evidence (sql/002)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_agent_registry import embed, fmt_vector
from load_evidence_seed import normalize_for_embed

import psycopg2

QUERY = (
    "Explain how this COBOL payment program calculates the account balance "
    "and determine whether its Java replacement preserves the behavior. "
    "cobol payment balance account CALC-BALANCE copybook"
)
# Lexical param: keyword phrase so plainto_tsquery AND-gate can fire on fixtures
# (full prose AND-query matches almost nothing). Dense still uses full QUERY.
LEXICAL_QUERY = "payment balance account"
TOP_K = 5
MIN_AUTHORITY = 0.5
# Junk has empty parents AND low auth; min_authority alone drops it.
REQUIRE_PARENT = False

# Product hybrid SQL (equivalent to sql/002_evidence_hybrid_retrieve.sql)
HYBRID_SQL = """
SELECT
  evidence_id,
  source_id,
  source_type,
  document_id,
  location,
  content,
  content_hash,
  source_authority,
  parent_evidence,
  (1.0 - (embedding <=> %s::vector))                         AS dense,
  ts_rank_cd(content_tsv, plainto_tsquery('english', %s))    AS lexical,
  source_authority                                           AS authority,
  CASE
    WHEN COALESCE(%s::boolean, false)
         AND cardinality(parent_evidence) = 0
    THEN 1.0
    ELSE 0.0
  END                                                        AS parent_penalty,
  (
    (1.0 - (embedding <=> %s::vector))
    + ts_rank_cd(content_tsv, plainto_tsquery('english', %s))
    + source_authority
    - CASE
        WHEN COALESCE(%s::boolean, false)
             AND cardinality(parent_evidence) = 0
        THEN 1.0
        ELSE 0.0
      END
  )                                                          AS score
FROM evidence
WHERE
  source_authority >= COALESCE(%s::real, 0.0)
  AND (
    %s::text[] IS NULL
    OR cardinality(%s::text[]) = 0
    OR source_type = ANY (%s::text[])
  )
  AND (
    NOT COALESCE(%s::boolean, false)
    OR cardinality(parent_evidence) > 0
  )
  AND (
    content_tsv @@ plainto_tsquery('english', %s)
    OR embedding IS NOT NULL
  )
ORDER BY score DESC, evidence_id
LIMIT GREATEST(COALESCE(%s::int, 10), 0)
"""

LEGACY_IDS = ("ev_copybook_01", "ev_cobol_src_01", "ev_db2_schema_01")
QUANT_ID = "ev_quant_pricing_01"
JUNK_ID = "ev_junk_low_auth"


def main() -> int:
    dsn = sys.argv[1] if len(sys.argv) > 1 else "dbname=david user=david host=127.0.0.1"
    qvec = fmt_vector(embed(normalize_for_embed(QUERY)))
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT evidence_id FROM evidence WHERE evidence_id = %s", (JUNK_ID,)
        )
        junk_exists = cur.fetchone() is not None

        cur.execute(
            HYBRID_SQL,
            (
                qvec,
                LEXICAL_QUERY,
                REQUIRE_PARENT,
                qvec,
                LEXICAL_QUERY,
                REQUIRE_PARENT,
                MIN_AUTHORITY,
                None,
                None,
                None,
                REQUIRE_PARENT,
                LEXICAL_QUERY,
                TOP_K,
            ),
        )
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT evidence_id FROM evidence
            WHERE source_authority >= %s
              AND evidence_id = %s
            """,
            (MIN_AUTHORITY, JUNK_ID),
        )
        junk_in_auth_filter = cur.fetchone() is not None
    conn.close()

    print(f"query={QUERY[:80]}...")
    print(f"lexical_query={LEXICAL_QUERY}")
    print(f"top_k={TOP_K} min_authority={MIN_AUTHORITY} require_parent={REQUIRE_PARENT}")
    print("rank\tevidence_id\tsource_type\tscore\tdense\tlexical\tauthority")
    ranked = []
    for i, row in enumerate(rows, 1):
        eid = row[0]
        stype = row[2]
        dense = float(row[9])
        lexical = float(row[10])
        authority = float(row[11])
        score = float(row[13])
        ranked.append(eid)
        print(
            f"{i}\t{eid}\t{stype}\tscore={score:.6f}\t"
            f"dense={dense:.6f}\tlexical={lexical:.6f}\tauthority={authority:.6f}"
        )

    junk_dropped = junk_exists and (JUNK_ID not in ranked) and (not junk_in_auth_filter)
    quant_not_first = QUANT_ID not in ranked or ranked[0] != QUANT_ID

    legacy_beat_quant = True
    for lid in LEGACY_IDS:
        if lid in ranked and QUANT_ID in ranked:
            if ranked.index(lid) > ranked.index(QUANT_ID):
                legacy_beat_quant = False
                break
        elif QUANT_ID in ranked and lid not in ranked:
            legacy_beat_quant = False
            break

    legacy_in_topk = all(lid in ranked for lid in LEGACY_IDS)
    if QUANT_ID not in ranked:
        legacy_beat_quant = legacy_in_topk or any(lid in ranked for lid in LEGACY_IDS)

    ok = junk_dropped and quant_not_first and legacy_beat_quant and legacy_in_topk

    print(f"junk_exists={junk_exists}")
    print(f"junk_dropped={junk_dropped}")
    print(f"legacy_in_topk={legacy_in_topk}")
    print(f"quant_not_preferred={quant_not_first and legacy_beat_quant}")
    print(f"pass={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
